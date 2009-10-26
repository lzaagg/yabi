from twisted.web2 import resource, http_headers, responsecode, http, server, fileupload
from twisted.internet import defer, reactor

import weakref
import sys, os
import stackless
import json
from MimeStreamDecoder import MimeStreamDecoder, no_intr

from Exceptions import PermissionDenied, InvalidPath
from globus.Auth import NoCredentials
from globus.CertificateProxy import ProxyInitError

from utils.stacklesstools import WaitForDeferredData
from utils.parsers import parse_url

from twisted.internet.defer import Deferred
from utils.FifoStream import FifoStream

DOWNLOAD_BLOCK_SIZE = 8192

class FileGetResource(resource.PostableResource):
    VERSION=0.1
    
    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path
        
        if not fsresource:
            raise Exception, "FileListResource must be informed on construction as to which FSResource is its parent"
        
        self.fsresource = weakref.ref(fsresource)
        
    def handle_get(self, request):
        if "uri" not in request.args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No uri provided\n")

        uri = request.args['uri'][0]
        scheme, address = parse_url(uri)
        
        # compile any credentials together to pass to backend
        creds={}
        for varname in ['key','password','username','cert']:
            if varname in request.args:
                creds[varname] = request.args[varname][0]
                del request.args[varname]
        
        # how many bytes to truncate the GET at
        bytes_to_read = int(request.args['bytes'][0]) if 'bytes' in request.args else None
        
        if not hasattr(address,"username"):
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "No username provided in uri\n")
        
        username = address.username
        path = address.path
        hostname = address.hostname
        
        basepath, filename = os.path.split(path)
        
        # get the backend
        fsresource = self.fsresource()
        if scheme not in fsresource.Backends():
            return http.Response( responsecode.NOT_FOUND, {'content-type': http_headers.MimeType('text', 'plain')}, "Backend '%s' not found\n"%scheme)
            
        bend = self.fsresource().GetBackend(scheme)
        
        # our client channel
        client_channel = defer.Deferred()
        
        def download_tasklet(req, channel):
            """Tasklet to do file download"""
            try:
                procproto, fifo = bend.GetReadFifo(hostname,username,basepath,filename,creds=creds)
            except NoCredentials, nc:
                return channel.callback(http.Response( responsecode.UNAUTHORIZED, {'content-type': http_headers.MimeType('text', 'plain')}, str(nc) ))
            
            while not procproto.isStarted():
                stackless.schedule()
            
            file = no_intr(open,fifo,"rb")
                
            # set file handle to be non blocking
            import fcntl, errno
            fcntl.fcntl(file.fileno(), fcntl.F_SETFL, os.O_NONBLOCK) 
            
            # datastream stores whether we have sent an ok response code yet
            datastream = False
            
            data = True
            while data:
                # because this is nonblocking, it might raise IOError 11
                data = no_intr(file.read,DOWNLOAD_BLOCK_SIZE)
                
                if data != True:
                    if len(data):
                        # we have data
                        if not datastream:
                            datastream = FifoStream(file, truncate=bytes_to_read)
                            datastream.prepush(data)
                            return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=datastream ))
                    else:
                        # end of fifo OR empty file.
                        # Did we error out? Wait until task is finished
                        while not procproto.isDone():
                            stackless.schedule()
                        
                        if procproto.exitcode:
                            return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Get failed: %s\n"%procproto.err ))
                        else:
                            # empty file successfully transfered
                            return channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('application', 'data')}, stream=data ))
                    
                stackless.schedule()
                
            return channel.callback(http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Catastrophic codepath violation. This error should never happen. It's a bug!" ))

        
        tasklet = stackless.tasklet(download_tasklet)
        tasklet.setup( request, client_channel )
        tasklet.run()
        
        return client_channel
    
    def http_POST(self, request):
        """
        Respond to a POST request.
        Reads and parses the incoming body data then calls L{render}.
    
        @param request: the request to process.
        @return: an object adaptable to L{iweb.IResponse}.
        """
        deferred = parsePOSTData(request)
        
        def post_parsed(result):
            return self.handle_get(request)
        
        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job Submission Failed %s\n"%res) )
        
        return deferred

    def http_GET(self, request):
        return self.handle_get(request)
    