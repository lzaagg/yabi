# -*- coding: utf-8 -*-
"""Web2 style resource that is gonna serve our children"""
from twisted.web2 import resource, http_headers, responsecode, http
import os, sys

##
## MANGO child
##

#os.environ['TWISTED_MANGO']='1'

#MANGO_APP = "yabiadmin"

## Environment setup for your Django project files:
#sys.path.append(os.path.join(os.path.dirname(__file__),MANGO_APP))
#os.environ['DJANGO_SETTINGS_MODULE'] = '%s.settings'%MANGO_APP

#from twisted.web2 import wsgi
#from django.conf import settings
#from django.core.management import setup_environ

#import yabiadmin.settings
#setup_environ(yabiadmin.settings)

#from django.core.handlers.wsgi import WSGIHandler

#def application1(environ, start):
    #os.environ['SCRIPT_NAME']=environ['SCRIPT_NAME']
    #if 'DJANGODEV' in environ:
        #os.environ['DJANGODEV']=environ['DJANGODEV']
    #if 'DJANGODEBUG' in environ:
        #os.environ['DJANGODEBUG']=environ['DJANGODEBUG']
    #result = WSGIHandler()(environ,start)
    ##print "result:\n\n",result
    #return result
    
#def application2(environ, start):
    #os.environ['SCRIPT_NAME']=environ['SCRIPT_NAME']
    #if 'DJANGODEV' in environ:
        #os.environ['DJANGODEV']=environ['DJANGODEV']
    #if 'DJANGODEBUG' in environ:
        #os.environ['DJANGODEBUG']=environ['DJANGODEBUG']
    #result = WSGIHandler()(environ,start)
    ##print "result:\n\n",result
    #return result
    
#def application3(environ, start):
    #os.environ['SCRIPT_NAME']=environ['SCRIPT_NAME']
    #if 'DJANGODEV' in environ:
        #os.environ['DJANGODEV']=environ['DJANGODEV']
    #if 'DJANGODEBUG' in environ:
        #os.environ['DJANGODEBUG']=environ['DJANGODEBUG']
    #result = WSGIHandler()(environ,start)
    ##print "result:\n\n",result
    #return result
    

    
##
## Filesystem resources
##
from fs.resource import FSResource

# backends

from fs.connector.LocalFilesystem import LocalFilesystem
from fs.connector.GridFTP import GridFTP
from fs.connector.SSHFilesystem import SSHFilesystem

##
## Execution resources
##
from ex.resource import ExecResource

# backends
from ex.connector.GlobusConnector import GlobusConnector
from ex.connector.SGEConnector import SGEConnector

VERSION = 0.2
class BaseResource(resource.PostableResource):
    """This is the baseclass for out "/" HTTP resource. It does nothing but defines the various children.
    It is also the location where you hook in you tools, or wsgi apps."""
    addSlash = True
    
    def __init__(self, *args, **kw):
        resource.PostableResource.__init__(self, *args, **kw)
        
        ##
        ## our handlers
        ##
        self.child_fs = FSResource()
        self.child_exec = ExecResource() 
        #self.child_yabiadmin = wsgi.WSGIResource(application1)
        #self.child_yabistore = wsgi.WSGIResource(application2)
        #self.child_yabife = wsgi.WSGIResource(application3)
        
    def LoadExecConnectors(self, quiet=False):
        self.child_exec.LoadConnectors(quiet)
        
    def LoadFSConnectors(self, quiet=False):
        self.child_fs.LoadConnectors(quiet)
        
    def LoadConnectors(self, quiet=False):
        self.LoadExecConnectors(quiet)
        self.LoadFSConnectors(quiet)
        
    def render(self, ctx):
        """Just returns a helpful text string"""
        return http.Response(responsecode.OK,
                        {'content-type': http_headers.MimeType('text', 'plain')},
                         "Twisted Yabi Core: %s\n"%VERSION)
