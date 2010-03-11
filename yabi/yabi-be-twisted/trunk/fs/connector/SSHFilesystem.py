# -*- coding: utf-8 -*-
import FSConnector
import globus
import stackless
from utils.parsers import *
from fs.Exceptions import PermissionDenied, InvalidPath
from FifoPool import Fifos
from twisted.internet import protocol
from twisted.internet import reactor
import os
import ssh

sshauth = ssh.SSHAuth.SSHAuth()

# a list of system environment variables we want to "steal" from the launching environment to pass into our execution environments.
ENV_CHILD_INHERIT = ['PATH']

# a list of environment variables that *must* be present for this connector to function
ENV_CHECK = []

# the schema we will be registered under. ie. schema://username@hostname:port/path/
SCHEMA = "ssh"

DEBUG = True

class SSHFilesystem(FSConnector.FSConnector, ssh.KeyStore.KeyStore, object):
    """This is the resource that connects to the globus gridftp backends"""
    VERSION=0.1
    NAME="SSH Filesystem"
    copymode = "ssh"
    
    def __init__(self):
        FSConnector.FSConnector.__init__(self)
        ssh.KeyStore.KeyStore.__init__(self)
        
    def mkdir(self, host, username, path, yabiusername=None, creds={}):
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        
        # If we don't have creds, get them
        if not creds:
            creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, path)
        
        usercert = self.save_identity(creds['key'])
        
        # we need to munge the path for transport over ssh (cause it sucks)
        mungedpath = '"' + path.replace('"',r'\"') + '"'
        pp = ssh.Shell.mkdir(usercert,host,mungedpath)
        
        while not pp.isDone():
            stackless.schedule()
            
        err, mkdir_data = pp.err, pp.out
        
        if pp.exitcode!=0:
            # error occurred
            if "Permission denied" in err:
                raise PermissionDenied(err)
            else:
                raise InvalidPath(err)
        
        if DEBUG:
            print "mkdir_data=",mkdir_data
            print "err", err
        
        return mkdir_data
        
    def rm(self, host, username, path, yabiusername=None, recurse=False, creds={}):
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        
        # If we don't have creds, get them
        if not creds:
            creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, path)
        
        usercert = self.save_identity(creds['key'])
        
        # we need to munge the path for transport over gsissh (cause it sucks)
        mungedpath = '"' + path.replace('"',r'\"') + '"'
        pp = ssh.Shell.rm(usercert,host,mungedpath,args="-r" if recurse else "")
        
        while not pp.isDone():
            stackless.schedule()
            
        err, rm_data = pp.err, pp.out
        
        if pp.exitcode!=0:
            # error occurred
            if "Permission denied" in err:
                raise PermissionDenied(err)
            else:
                raise InvalidPath(err)
        
        if DEBUG:
            print "rm_data=",rm_data
            print "err", err
        
        return rm_data
    
    def ls(self, host, username, path, yabiusername=None, recurse=False, culldots=True, creds={}):
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        
        if DEBUG:
            print "GridFTP::ls(",host,username,path,yabiusername,recurse,culldots,creds,")"
        
        # If we don't have creds, get them
        if not creds:
            creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, path)
        
        usercert = self.save_identity(creds['key'])
        
        # we need to munge the path for transport over gsissh (cause it sucks)
        mungedpath = '"' + path.replace('"',r'\"') + '"'
        pp = ssh.Shell.ls(usercert,host,mungedpath, args="-alFR" if recurse else "-alF" )
        
        while not pp.isDone():
            stackless.schedule()
            
        err, out = pp.err, pp.out
        
        if pp.exitcode!=0:
            # error occurred
            if "Permission denied" in err:
                raise PermissionDenied(err)
            else:
                raise InvalidPath(err)
        
        ls_data = parse_ls(out, culldots=culldots)
        
        if DEBUG:
            print "ls_data=",ls_data
            print "out", out
            print "err", err
        
        # are we non recursive?
        if not recurse:
            # "None" path header is actually our path
            ls_data[path]=ls_data[None]
            del ls_data[None]
                        
        os.unlink(usercert)
                        
        return ls_data
        
    def GetWriteFifo(self, host=None, username=None, path=None, filename=None, fifo=None, yabiusername=None, creds={}):
        """sets up the chain needed to setup a write fifo from a remote path as a certain user.
        
        pass in here the username, path
    
        if a fifo pathis apssed in, use that one instead of making one
    
        when everything is setup and ready, deferred will be called with (proc, fifo), with proc being the python subprocess Popen object
        and fifo being the filesystem location of the fifo.
        """
        if DEBUG:
            print "SSHFilesystem::GetWriteFifo( host:"+host,",username:",username,",path:",path,",filename:",filename,",fifo:",fifo,",yabiusername:",yabiusername,",creds:",creds,")"
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        
        dst = "%s@%s:%s"%(username,host,os.path.join(path,filename))
        
        # make sure we are authed
        if not creds:
            creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, path)
            
        usercert = self.save_identity(creds['key'])
        
        pp, fifo = ssh.Copy.WriteToRemote(usercert,dst,fifo=fifo)
        
        return pp, fifo
    
    def GetReadFifo(self, host=None, username=None, path=None, filename=None, fifo=None, yabiusername=None, creds={}):
        """sets up the chain needed to setup a read fifo from a remote path as a certain user.
        
        pass in here the username, path, and a deferred
    
        if a fifo pathis apssed in, use that one instead of making one
    
        when everything is setup and ready, deferred will be called with (proc, fifo), with proc being the python subprocess Popen object
        and fifo being the filesystem location of the fifo.
        """
        assert yabiusername or creds, "You must either pass in a credential or a yabiusername so I can go get a credential. Neither was passed in"
        dst = "%s@%s:%s"%(username,host,os.path.join(path,filename))
        
        # make sure we are authed
        if not creds:
            creds = sshauth.AuthProxyUser(yabiusername, SCHEMA, username, host, path)
            
        usercert = self.save_identity(creds['key'])
        
        pp, fifo = ssh.Copy.ReadFromRemote(usercert,dst,fifo=fifo)
        
        return pp, fifo
       