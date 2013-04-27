# -*- coding: utf-8 -*-
### BEGIN COPYRIGHT ###
#
# (C) Copyright 2011, Centre for Comparative Genomics, Murdoch University.
# All rights reserved.
#
# This product includes software developed at the Centre for Comparative Genomics
# (http://ccg.murdoch.edu.au/).
#
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, YABI IS PROVIDED TO YOU "AS IS,"
# WITHOUT WARRANTY. THERE IS NO WARRANTY FOR YABI, EITHER EXPRESSED OR IMPLIED,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT OF THIRD PARTY RIGHTS.
# THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF YABI IS WITH YOU.  SHOULD
# YABI PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR
# OR CORRECTION.
#
# TO THE EXTENT PERMITTED BY APPLICABLE LAWS, OR AS OTHERWISE AGREED TO IN
# WRITING NO COPYRIGHT HOLDER IN YABI, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR
# REDISTRIBUTE YABI AS PERMITTED IN WRITING, BE LIABLE TO YOU FOR DAMAGES, INCLUDING
# ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE
# USE OR INABILITY TO USE YABI (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR
# DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES
# OR A FAILURE OF YABI TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER
# OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
#
### END COPYRIGHT ###
# -*- coding: utf-8 -*-

import TaskManager

Tasks = TaskManager.TaskManager()

from Tasklets import tasklets

from conf import config

import gevent


def startup():
    """Start up the TaskManager, so it can go and get some jobs..."""
    print "Starting TaskManager..."
    Tasks.start()

    # load up saved tasklets
    print "Loading Tasks..."
    tasklets.load(directory=config.config['backend']['tasklets'])
    print "Tasks loaded"


def shutdown():
    """pickle tasks to disk"""
    print "Saving tasklets..."

    # we need to make sure any new tasklets that are just starting start up...
    # trying to fix 'requested' shutdown problem.
    Tasks.stop()

    # wait for any left overs to start
    gevent.sleep(1.0)

    tasklets.save(directory=config.config['backend']['tasklets'])

from twistedweb2 import resource, http_headers, responsecode, http


# the following is used for the yabitests backend start stop tests, to check that serialised tasks are resumed correctly
class TaskManagerResource(resource.Resource):
    """When this resource is hit... tasklets are purged"""
    VERSION = 0.2
    addSlash = True

    def __init__(self, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)

    def render(self, request):
        #tasklets.purge()

        return http.Response(responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, tasklets.debug_json())


class TaskManagerPickleResource(resource.Resource):
    """This is the resource that connects to all the filesystem backends"""
    VERSION = 0.2
    addSlash = True

    def __init__(self, *args, **kwargs):
        resource.Resource.__init__(self, *args, **kwargs)

    def render(self, request):
        tasklets.purge()
        gevent.sleep()
        return http.Response(responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, tasklets.pickle())
