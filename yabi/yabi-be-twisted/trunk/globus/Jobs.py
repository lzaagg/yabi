"""
Jobs
====
This is an object that keeps track of presently running globus jobs.

"""
import tempfile
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
import globus 
import os, json
from twisted.web import client

class _StreamReader(object):
    """Process a stream's data using callbacks for data and stream finish."""

    def __init__(self, stream, gotDataCallback, polldelay=1.0):
        self.stream = stream
        self.gotDataCallback = gotDataCallback
        self.result = Deferred()
        self.polldelay = polldelay

    def run(self):
        # self.result may be del'd in _read()
        result = self.result
        self._read()
        return result
    
    def _read(self):
        try:
            result = self.stream.read()
        except:
            self._gotError(Failure())
            return
        if isinstance(result, Deferred):
            result.addCallbacks(self._gotData, self._gotError)
        else:
            self._gotData(result)

    def _gotError(self, failure):
        result = self.result
        del self.result, self.gotDataCallback, self.stream
        result.errback(failure)
    
    def _gotData(self, data):
        if data is None:
            result = self.result
            del self.result, self.gotDataCallback, self.stream
            result.callback(None)
            return
        try:
            self.gotDataCallback(data)
        except:
            self._gotError(Failure())
            return
        reactor.callLater(self.polldelay, self._read)

def readStream(stream, gotDataCallback, polldelay=1.0):
    """Pass a stream's data to a callback.

    Returns Deferred which will be triggered on finish.  Errors in
    reading the stream or in processing it will be returned via this
    Deferred.
    """
    return _StreamReader(stream, gotDataCallback, polldelay).run()



def JobPollGeneratorDefault():
    """Generator for these MUST be infinite. Cause you don't know how long the job will take. Default is to hit it pretty hard."""
    while True:
        yield 2.0

class Jobs(object):
    STREAM_POLL_INTERVAL = 1.0              # for stream reading thats not that important, check every this many seconds
    
    def __init__(self,authproxy,backend):
        # store the job info in here. Key is job uuid. Values are just a list
        self._jobs={}
        self.authproxy = authproxy
        self.backend = backend
    
    def AddJob(self,uuid,username,epr,callback=None,errback=None, termtime=None, poll=None):
        """Add a job to the pool. callback will be called each time the job status changes.
        
        poll is a generator that returns how often to check the status
        """
        if poll==None:
            poll=JobPollGeneratorDefault()
        
        # save the epr to a tempfile so we can use it again and again
        temp = tempfile.NamedTemporaryFile(suffix=".epr",delete=False)
        temp.write(epr)
        temp.close()
         
        self._jobs[uuid] = [None,username, epr,temp.name,termtime,poll,callback,errback]
        
        reactor.callLater( poll.next(), self.CheckJob, uuid)
        
    def CheckJob(self, uuid):
        """Check the status of the job. If it has changed, call the jobs callback"""
        #print "CheckJob",uuid
        status, username, epr, eprfile, termtime, poll, callback, errback = self._jobs[uuid]
        
        # get the remote status.
        def check_job_status():
            usercert = self.authproxy.ProxyFile(username)
            proc = globus.Run.status(usercert,eprfile)
            
            # when proc returns... we want to do the following
            def _status_returned(data):
                if len(data):
                    assert data.startswith("Current job state:"), "Check Job failed. Full error follows:\n\n%s\n"%data
                    
                    state = data.split(":")[-1].strip()
                    
                    #print "job %s state: %s"%(uuid,state)
                    
                    if state!=status:
                        # state has changed.
                        #print "state changed. calling callback..."
                        callback(uuid,state)
                        self._jobs[uuid][0]=state
                    
                    if state!="Done":
                        # schedule to check again
                        reactor.callLater( poll.next(), self.CheckJob, uuid )
                    else:
                        # job is done... do we remove it from the cache... I guess we do... and all the files...
                        self.DeleteJob(uuid)
                    
            deferred = readStream(proc.stdout, _status_returned, self.STREAM_POLL_INTERVAL)
            
            # if anything goes wrong, call our associated error callback, which should report it to the user i suppose.
            deferred.addErrback( lambda res: self.DeleteJob(uuid) and errback(uuid,res) )
            
        # get the remote status.
        # first we need to auth, if not authed already
        if not self.authproxy.IsProxyValid(username):
            # we have to auth the user. we need to get the credentials json object from the admin mango app
            self.AuthProxyUser(username,self.backend, check_job_status, errback)
        else:
            # auth our user
            check_job_status()
        
        
    def DeleteJob(self,uuid):
        status, username, epr, eprfile, termtime, poll, callback, errback = self._jobs[uuid]
        os.unlink(eprfile)
        del self._jobs[uuid]
        return True
    
    def AuthProxyUser(self, username, backend, successcallback, errorcb):
        """Try to auth the user noninteractively"""
        host,port = "localhost",8000
        useragent = "YabiFS/0.1"
        
        factory = client.HTTPClientFactory(
            'http://%s:%d/yabiadmin/ws/credential/%s/%s/'%(host,port,username,backend),
            agent = useragent
            )
        reactor.connectTCP(host, port, factory)
        
        # now if the page fails for some reason. deal with it
        def _doFailure(data):
            print "Job _doFailure:",factory,":",type(data),data.__class__
            print data
            
            errorcb("User: %s does not have credentials for this backend\n"%username)
            
        # if we get the credentials decode them and auth them
        def _doSuccess(data):
            print "Job _doSuccess"
            credentials=json.loads(data)
            print "Credentials gathered successfully for user %s"%username
            
            # auth the user
            self.authproxy.CreateUserProxy(username,credentials['cert'],credentials['key'],credentials['password'])
            
            successcallback()
        
        return factory.deferred.addCallback(_doSuccess).addErrback(_doFailure)
