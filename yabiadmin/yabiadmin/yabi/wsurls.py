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

from django.conf.urls import *

# frontend webservices
urlpatterns = patterns(
    'yabiadmin.yabi.ws_frontend_views',
    url(r'^tool/(?P<toolname>[^/]*)(/(?P<toolid>\d+))?/?$', 'tool', name='tool'),
    url(r'^menu[/]*$', 'menu', name='menu'),
    url(r'^menu_saved_workflows[/]*$',
        'menu_saved_workflows', name='menu_saved_workflows'),

    url(r'^fs/ls[/]*$', 'ls', name='ls'),
    url(r'^fs/get[/]*$', 'get', name='get'),
    url(r'^fs/zget[/]*$', 'zget', name='zget'),
    url(r'^fs/put[/]*$', 'put', name='put'),
    url(r'^fs/copy[/]*$', 'copy', name='copy'),
    url(r'^fs/rcopy[/]*$', 'rcopy', name='rcopy'),
    url(r'^fs/rm[/]*$', 'rm', name='rm'),
    url(r'^fs/mkdir/?$', 'mkdir', name='mkdir'),

    url(r'^workflows/submit[/]*$', 'submit_workflow'),
    url(r'^workflows/save[/]*$', 'save_workflow'),
    url(r'^workflows/delete[/]*$', 'delete_workflow'),
    url(r'^workflows/delete_saved[/]*$', 'delete_saved_workflow'),
    url(r'^workflows/get/(?P<workflow_id>\d+)[/]*$', 'get_workflow'),
    url(r'^workflows/datesearch[/]*$', 'workflow_datesearch'),
    url(r'^workflows/(?P<id>\d+)/tags[/]*$', 'workflow_change_tags'),

    url(r'^account/credential[/]*$', 'credential', name='credential'),
    url(r'^account/credential/([0-9]+)[/]*$', 'save_credential', name='save_credential'),
    url(r'^account/passchange[/]*$', 'passchange', name="passchange"),
)

# admin support pages
urlpatterns += patterns(
    'yabiadmin.yabi.adminviews',
    url(r'^manage_credential[/]*$', 'duplicate_credential'),
    url(r'^modify_backend/id/(?P<id>\d+)[/]*$', 'modify_backend_by_id'),
    url(r'^modify_backend/name/(?P<scheme>[a-zA-Z_]*[a-zA-Z0-9_\-\.]*)/(?P<hostname>[a-zA-Z_]*[a-zA-Z0-9_\-\.]*)[/]*$', 'modify_backend_by_name'),
)

# yabish webservices
urlpatterns += patterns(
    'yabiadmin.yabi.ws_yabish_views',
    url(r'^yabish/submitjob/?$', 'submitjob', name='submitjob'),
    url(r'^yabish/createstageindir/?$', 'createstageindir', name='createstageindir'),
    url(r'^yabish/is_stagein_required/?$', 'is_stagein_required', name='is_stagein_required'),
    url(r'^yabish/backends/?$', 'list_backends', name='list_backends'),
)
