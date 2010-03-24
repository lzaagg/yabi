# -*- coding: utf-8 -*-
from ExecConnector import ExecConnector, ExecutionError

# a list of system environment variables we want to "steal" from the launching environment to pass into our execution environments.
ENV_CHILD_INHERIT = ['PATH']

# a list of environment variables that *must* be present for this connector to function
ENV_CHECK = []

# the schema we will be registered under. ie. schema://username@hostname:port/path/
SCHEMA = "ssh"

DEBUG = False

from twisted.web2 import http, responsecode, http_headers, stream

import shlex
import globus
import stackless
import tempfile

from utils.stacklesstools import sleep
import ssh

class SSHConnector(ExecConnector):
    def __init__(self):
        ExecConnector.__init__(self)
    
    def run(self, yabiusername, command, working, scheme, username, host, channel, stdout="STDOUT.txt", stderr="STDERR.txt", maxWallTime=60, maxMemory=1024, cpus=1, queue="testing", jobType="single", **creds):
        client_stream = stream.ProducerStream()
        channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream = client_stream ))
        stackless.schedule()
        
        try:
            if DEBUG:
                print "SSH",command,"WORKING:",working    
            client_stream.write("Unsubmitted\n")
            stackless.schedule()
            
            client_stream.write("Pending\n")
            stackless.schedule()
            
            pp = ssh.Run.run()
            client_stream.write("Running\n")
            stackless.schedule()
            
            while not pp.isDone():
                stackless.schedule()
                
            if pp.exitcode==0:
                # success
                client_stream.write("Done\n")
                client_stream.finish()
                return
                
            # error
            print "SSH Job error:"
            print "OUT:",pp.out
            print "ERR:",pp.err
            client_stream.write("Error\n")
            client_stream.finish()
            return
                    
        except Exception, ee:
            import traceback
            traceback.print_exc()
            client_stream.write("Error\n")
            client_stream.finish()
            return
        