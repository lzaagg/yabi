# -*- coding: utf-8 -*-
from twisted.web2 import resource, http_headers, responsecode, http, stream
from twisted.internet import defer

import weakref

from utils.submit_helpers import parsePOSTDataRemoteWriter

from TaskManager.Tasklets import tasklets
import stackless
from utils.parsers import parse_url

import json

DEBUG = False

class ExecInfoResource(resource.PostableResource):
    VERSION=0.1

    def __init__(self,request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path

        if not fsresource:
            raise Exception, "FileListResource must be informed on construction as to which FSResource is its parent"

        self.fsresource = weakref.ref(fsresource)

    def handle_info(self,request):
        args = request.args

        if "yabiusername" not in args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "Task info must have a yabiusername set (so we can get credentials)!\n")
        yabiusername = args['yabiusername'][0]

        if "taskid" not in args:
            return http.Response( responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "Task info must have a taskid!\n")
        taskid = int(args['taskid'][0])

        # we are gonna try submitting the job. We will need to make a deferred to return, because this could take a while
        #client_stream = stream.ProducerStream()
        client_deferred = defer.Deferred()

        def report_task_info(channel,tid):
            matching_tasks = [X for X in tasklets.tasks if X.taskid==tid]
            
            if not matching_tasks:
                channel.callback(http.Response( responsecode.NOT_FOUND, {'content-type': http_headers.MimeType('text', 'plain')}, "Task %d not found\n"%tid ))
                return
                
            if len(matching_tasks)>1:
                channel.callback(http.Response( responsecode.SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "More than one task found with id: %d\n"%tid ))
                return
                
            task = matching_tasks[0]
            
            # get the backend
            taskuri = task.json['exec']['backend']
            
            scheme, address = parse_url(taskuri)
            fsresource = self.fsresource()
            if scheme not in fsresource.Backends():
                return http.Response( responsecode.NOT_FOUND, {'content-type': http_headers.MimeType('text', 'plain')}, "Backend '%s' not found\n"%scheme)
            bend = self.fsresource().GetBackend(scheme)
            
            client_stream = stream.ProducerStream()
            channel.callback(http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream = client_stream ))
            
            print bend.get_all_running()
            
            client_stream.write(json.dumps(bend.get_running(task._jobid)))
            client_stream.finish()

        info_task = stackless.tasklet(report_task_info)
        info_task.setup(client_deferred, taskid)
        info_task.run()

        return client_deferred
        #return http.Response( responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, stream = client_stream )

    def http_POST(self, request):
        """
        Respond to a POST request.
        Reads and parses the incoming body data then calls L{render}.

        @param request: the request to process.
        @return: an object adaptable to L{iweb.IResponse}.
        """
        deferred = parsePOSTDataRemoteWriter(request)

        def post_parsed(result):
            return self.handle_info(request)

        deferred.addCallback(post_parsed)
        deferred.addErrback(lambda res: http.Response( responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, "Job info Failed %s\n"%res) )

        return deferred

    def http_GET(self, request):
        return self.handle_info(request)
