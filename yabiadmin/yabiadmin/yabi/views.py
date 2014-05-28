# -*- coding: utf-8 -*-
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
# -*- coding: utf-8 -*-
import httplib
from urllib import urlencode
import copy
import os
from django.conf.urls.defaults import *
from django.conf import settings
from django.http import HttpResponse
import logging
logger = logging.getLogger(__name__)


# proxy view to pass through all requests set up in urls.py
def proxy(request, url, server, base):
    logger.debug(url)
    logger.debug(server)
    logger.debug(base)

    # TODO CODEREVIEW
    # Is is possible to post to a page and still send get params,
    # are they dropped by this proxy. Would it be possible to override yabiusername by
    # crafting a post and sending yabiusername as a get param as well

    if request.method == "GET":
        # resource = "%s?%s" % (os.path.join(base, url), request.META['QUERY_STRING']+"&yabiusername=%s"%quote(request.user.username) )
        resource = "%s?%s" % (os.path.join(base, url), request.META['QUERY_STRING'])
        logger.debug('Proxying get: %s%s' % (server, resource))
        conn = httplib.HTTPConnection(server)
        conn.request(request.method, resource)
        r = conn.getresponse()

    elif request.method == "POST":
        resource = os.path.join(base, url)
        post_params = copy.copy(request.POST)
        # post_params['yabiusername'] = request.user.username
        logger.debug('Proxying post: %s%s' % (server, resource))
        data = urlencode(post_params)
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = httplib.HTTPConnection(server)
        conn.request(request.method, resource, data, headers)
        r = conn.getresponse()

    data = r.read()
    response = HttpResponse(data, status=int(r.status))

    if r.getheader('content-disposition', None):
        response['content-disposition'] = r.getheader('content-disposition')

    if r.getheader('content-type', None):
        response['content-type'] = r.getheader('content-type')

    return response


def status_page(request):
    """Availability page to be called to see if yabiadmin is running. Should return HttpResponse with status 200"""
    logger.info('')

    # write a file
    with open(os.path.join(settings.WRITABLE_DIRECTORY, 'status_page_testfile.txt'), 'w') as f:
        f.write("testing file write")

    # read it again
    with open(os.path.join(settings.WRITABLE_DIRECTORY, 'status_page_testfile.txt'), 'r') as f:
        contents = f.read()
        assert 'testing file write' in contents

    # delete the file
    os.unlink(os.path.join(settings.WRITABLE_DIRECTORY, 'status_page_testfile.txt'))

    return HttpResponse('Status OK')
