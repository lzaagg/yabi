# -*- coding: utf-8 -*-
from twisted.web import client
from twisted.web.client import HTTPPageDownloader
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python import failure, log

import os, types

class CallbackHTTPClient(client.HTTPPageGetter):
    def __init__(self, *args, **kwargs):
        self.callback = None
        self.errordata = None
    
    def SetCallback(self, callback):
        self.callback = callback
    
    #def lineReceived(self, line):
        #print "LINE_RECEIVED:",line
        #return client.HTTPPageGetter.lineReceived(self,line)
    
    # ask for page as HTTP/1.1 so we get chunked response
    def sendCommand(self, command, path):
        self.transport.write('%s %s HTTP/1.0\r\n' % (command, path))
        
    # capture "connection:close" so we stay HTTP/1.1 keep alive!
    def sendHeader(self, name, value):
        if name.lower()=="connection" and value.lower()=="close":
            return 
        return client.HTTPPageGetter.sendHeader(self,name,value)
    
    def rawDataReceived(self, data):
        if int(self.status) != 200:
            # we got an error. TODO: something graceful here
            self.errordata=data
            
        elif self.callback:
            # hook in here to process chunked updates
            lines=data.split("\r\n")
            print "LINES",[lines]
            #chunk_size = int(lines[0].split(';')[0],16)
            #chunk = lines[1]
            chunk = lines[0]
            
            #assert len(chunk)==chunk_size, "Chunked transfer decoding error. Chunk size mismatch"
            
            # run the callback in a tasklet!!! Stops scheduler getting into a looped blocking state
            reporter=tasklet(self.callback)
            reporter.setup(chunk)
            reporter.run()
            
        else:
            pass
        #print "RECV",data
        return client.HTTPPageGetter.rawDataReceived(self,data)

class CallbackHTTPPageGetter(client.HTTPPageGetter,CallbackHTTPClient):
    pass


class CallbackHTTPPageDownloader(client.HTTPPageDownloader,CallbackHTTPClient):
    pass


class CallbackHTTPClientFactory(client.HTTPClientFactory):
    protocol = CallbackHTTPClient
    
    def __init__(self, url, method='GET', postdata=None, headers=None,
                 agent="Twisted PageGetter", timeout=0, cookies=None,
                 followRedirect=True, redirectLimit=20, callback=None):
        self._callback=callback
        return client.HTTPClientFactory.__init__(self, url, method, postdata, headers, agent, timeout, cookies, followRedirect, redirectLimit)
    
    def buildProtocol(self, addr):
        #print "bp",addr
        p = client.HTTPClientFactory.buildProtocol(self, addr)
        p.SetCallback(self._callback)
        self.last_client = p
        return p

    def SetCallback(self, callback):
        self._callback=callback

class CallbackHTTPDownloader(CallbackHTTPClientFactory):
    """Download to a file."""

    protocol = CallbackHTTPPageDownloader
    value = None

    def __init__(self, url, fileOrName,
                 method='GET', postdata=None, headers=None,
                 agent="Twisted client", supportPartial=0,
                 timeout=0, cookies=None, followRedirect=1,
                 redirectLimit=20):
        self.requestedPartial = 0
        if isinstance(fileOrName, types.StringTypes):
            self.fileName = fileOrName
            self.file = None
            if supportPartial and os.path.exists(self.fileName):
                fileLength = os.path.getsize(self.fileName)
                if fileLength:
                    self.requestedPartial = fileLength
                    if headers == None:
                        headers = {}
                    headers["range"] = "bytes=%d-" % fileLength
        else:
            self.file = fileOrName
        CallbackHTTPClientFactory.__init__(
            self, url, method=method, postdata=postdata, headers=headers,
            agent=agent, timeout=timeout, cookies=cookies,
            followRedirect=followRedirect, redirectLimit=redirectLimit)


    def gotHeaders(self, headers):
        CallbackHTTPClientFactory.gotHeaders(self, headers)
        if self.requestedPartial:
            contentRange = headers.get("content-range", None)
            if not contentRange:
                # server doesn't support partial requests, oh well
                self.requestedPartial = 0
                return
            start, end, realLength = http.parseContentRange(contentRange[0])
            if start != self.requestedPartial:
                # server is acting wierdly
                self.requestedPartial = 0


    def openFile(self, partialContent):
        if partialContent:
            file = open(self.fileName, 'rb+')
            file.seek(0, 2)
        else:
            file = open(self.fileName, 'wb')
        return file

    def pageStart(self, partialContent):
        """Called on page download start.

        @param partialContent: tells us if the download is partial download we requested.
        """
        if partialContent and not self.requestedPartial:
            raise ValueError, "we shouldn't get partial content response if we didn't want it!"
        if self.waiting:
            try:
                if not self.file:
                    self.file = self.openFile(partialContent)
            except IOError:
                #raise
                self.deferred.errback(failure.Failure())

    def pagePart(self, data):
        if not self.file:
            return
        try:
            self.file.write(data)
        except IOError:
            #raise
            self.file = None
            self.deferred.errback(failure.Failure())
            

    def noPage(self, reason):
        """
        Close the storage file and errback the waiting L{Deferred} with the
        given reason.
        """
        if self.waiting:
            self.waiting = 0
            if self.file:
                try:
                    self.file.close()
                except:
                    log.err(None, "Error closing HTTPDownloader file")
            self.deferred.errback(reason)


    def pageEnd(self):
        self.waiting = 0
        if not self.file:
            return
        try:
            self.file.close()
        except IOError:
            self.deferred.errback(failure.Failure())
            return
        self.deferred.callback(self.value)

