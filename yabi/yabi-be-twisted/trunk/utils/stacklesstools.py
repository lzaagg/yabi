# -*- coding: utf-8 -*-
"""A suite of tools for using twisted with stackless python. Turns the twisted callback methods into
functions that block a stackless tasklet.
"""

from twisted.web import client
from twisted.web.client import HTTPPageDownloader
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

import urllib
import time
import json
import os, types

from stackless import schedule, tasklet

from CallbackHTTPClient import CallbackHTTPClient, CallbackHTTPClientFactory, CallbackHTTPDownloader
from RememberingHTTPClient import RememberingHTTPClient, RememberingHTTPClientFactory, RememberingHTTPDownloader

DEBUG = False

from conf import config

USER_AGENT = "YabiStackless/0.1"

## errors
class GETFailure(Exception): pass
class DeferredError(Exception): pass
class CloseConnections(Exception):
    """A special exception raised in tasklets by the engine shutdown.
    It closes all the open tcp connections associated with this tasklet and then retries the last event.
    """
    pass

def sleep(seconds):
    """Sleep the tasklet for this many seconds"""
    wakeup = time.time()+seconds
    while time.time()<wakeup:
        schedule()

import urllib

#def GET(path, host=WS_HOST, port=WS_PORT, factory_class=CallbackHTTPClientFactory,**kws):
def GET(path, host=None, port=None, factory_class=RememberingHTTPClientFactory,**kws):
    """Stackless integrated twisted webclient GET
    Pass in the path to get and optionally the host and port
    raises a GETFailure exception on failure
    returns the return code and data on success 
    """
    # defaults to us
    host=host or config.config['backend']['port'][0]
    host = "127.0.0.1" if host=="0.0.0.0" else host
    port=port or config.config['backend']['port'][1]
    
    getdata=urllib.urlencode(kws)
    
    if DEBUG:
        print "=>",str("http://%s:%d%s"%(host,port,path+"?"+getdata))
        
    fullpath=str("http://%s:%d%s"%(host,port,path))
    if getdata:
        fullpath += "?"+getdata
        
    factory = factory_class(
        fullpath,
        agent = USER_AGENT,
        
        )
    factory.noisy=False
    
    if DEBUG:
        print "GETing",fullpath
    
    # switches to trigger the unblocking of the stackless thread
    get_complete = [False]
    get_failed = [False]
    
    # now if the get fails for some reason. deal with it
    def _doFailure(data):
        if isinstance(data,Failure):
            exc = data.value
            #get_failed[0] = -1, str(exc), "Tried to GET %s"%(fullpath)
            get_failed[0] = -1, str(exc), "Tried to GET %s.\nRemote response was:\n%s"%(fullpath,factory.last_client.errordata)
        else:
            get_failed[0] = int(factory.status), factory.message, "Remote host %s:%d%s said: %s"%(host,port,path,factory.last_client.errordata)
        
    def _doSuccess(data):
        if DEBUG:
            print "SUCCESS:",factory.status,factory.message, data
        get_complete[0] = int(factory.status), factory.message, data
    
    # start the connection
    factory.deferred.addCallback(_doSuccess).addErrback(_doFailure)
    reactor.connectTCP(host, port, factory)

    # now we schedule this thread until the task is complete
    while not get_complete[0] and not get_failed[0]:
        if DEBUG:
            print "G",get_complete[0],"G2",get_failed[0]
        schedule()
        
    if get_failed[0]:
        if DEBUG:
            print "get_failed=",get_failed
        if type(get_failed[0])==tuple and len(get_failed[0])==3:
            # failed naturally
            raise GETFailure(get_failed[0])
        elif get_failed[0]==True:
            # failed by tasklet serialisation and restoration
            return GET(path, host, port, factory_class, **kws)
        else:
            #print "GETFailed=",get_failed
            assert False, "got unknown GET failure response"
    
    return get_complete[0]

def POST(path,**kws):
    """Stackless integrated twisted webclient POST"""
    if 'host' in kws:
        host = kws['host']
        del kws['host']
    else:
        host = config.config['backend']['port'][0]
        host = "127.0.0.1" if host=="0.0.0.0" else host
        
    if 'port' in kws:
        port = kws['port']
        del kws['port']
    else:
        port = config.config['backend']['port'][1]
        
    errorpage=[None]
        
    if 'datacallback' in kws:
        datacallback = kws['datacallback']
        del kws['datacallback']
    else:
        datacallback = None
    
    postdata=urllib.urlencode(kws)
    #postdata="src=gridftp1/cwellington/bi01/cwellington/test&dst=gridftp1/cwellington/bi01/cwellington/test2"
    #print "POST DATA:",postdata
    
    factory = CallbackHTTPClientFactory(
        str("http://%s:%d%s"%(host,port,path)),
        agent = USER_AGENT,
        method="POST",
        postdata=postdata,
        headers={
            'Content-Type':"application/x-www-form-urlencoded",
            'Accept':'*/*',
            'Content-Length':"65"
            },
        callback=datacallback
        )
        
    factory.noisy=False
        
    get_complete = [False]
    get_failed = [False]
    
    # now if the get fails for some reason. deal with it
    def _doFailure(data):
        if isinstance(data,Failure):
            exc = data.value
            get_failed[0] = -1, str(exc), "Tried to POST %s to %s.\nRemote response was:\n%s"%(postdata,str("http://%s:%d%s"%(host,port,path)),factory.last_client.errordata)
        else:
            get_failed[0] = int(factory.status), factory.message, "Remote host %s:%d%s said: %s"%(host,port,path,factory.last_client.errordata)
    
    def _doSuccess(data):
        #print "Post success"
        get_complete[0] = int(factory.status), factory.message, data
        
    factory.deferred.addCallback(_doSuccess).addErrback(_doFailure)

    reactor.connectTCP(host, port, factory)
    
    # now we schedule this thread until the task is complete
    while not get_complete[0] and not get_failed[0]:
        #print "P"
        schedule()
        
    if get_failed[0]:
        if type(get_failed[0])==tuple and len(get_failed[0])==3:
            # failed naturally
            raise GETFailure(get_failed[0])
        elif get_failed[0]:
            # failed by tasklet serialisation and restoration
            return POST(path, host=host, port=port, datacallback=datacallback, **kws)
        else:
            #print "POSTFailed=",get_failed
            assert False, "got unknown POST failure response"
    
    return get_complete[0]


def WaitForDeferredData(deferred):
    """Causes a stackless thread to wait until data is available on a deferred, then returns that data.
    If an errback chain is called, it raises an DeferredError exception with the contents as the error 
    passthrough (probably a Failure intsance)
    """
    if not isinstance(deferred,Deferred):
        return deferred
    
    cont = [False]                  # continue?
    data = [None]                   # data that we will be passed and will pass on
    err = [None]                    # the failure if errbacks are called
    
    def _cont(dat):
        cont[0] = True              # unblock
        data[0] = dat               # pass out the data
        return True
        
    def _err(dat):
        cont[0] = True
        err[0] = dat
        return False
        
    deferred.addCallback(_cont)     # trigger our callback on data
    
    while not cont[0]:
        schedule()                  # sleep the thread until we are asked to continue
        
    if err[0]:
        raise DeferredError, err[0]
    
    return data[0]

def AdminBackoffSchedule():
    """Generator that generates the various delays to wait between retries when admin fails"""
    delay = 1.0
    while delay<1000.0:
        yield delay
        delay*=2
        
def RetryCall(call, *args, **kwargs):
    delays = AdminBackoffSchedule()
    while True:
        try:
            result = call(*args, **kwargs)
            print "<================",result
            return result
        except GETFailure, gf:
            print "!!!!!!!!!!!!!!!!!",gf
            try:
                sleep(delays.next())
            except StopIteration:
                raise gf
        
# two curried functions
RetryPOST = lambda *a,**b: RetryCall(POST,*a,**b)
RetryGET = lambda *a,**b: RetryCall(GET,*a,**b)