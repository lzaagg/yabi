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
from django.conf import settings
from django.core import urlresolvers
from django.contrib import admin as djangoadmin
from django.views.generic.base import RedirectView
from yabi.yabi import admin

djangoadmin.autodiscover()

urlpatterns = patterns('yabi.yabifeapp.views',
                       url(r'^status_page[/]*$', 'status_page', name='status_page'),
                       (r'^preview/metadata[/]*$', 'preview_metadata'),
                       (r'^preview[/]*$', 'preview'),
                       (r'^[/]*$', 'design'),
                       (r'^account/password[/]*$', 'password'),
                       (r'^account[/]*$', 'account'),
                       (r'^design/reuse/(?P<id>.*)[/]*$', 'design'),
                       (r'^design[/]*$', 'design'),
                       (r'^jobs[/]*$', 'jobs'),
                       (r'^files[/]*$', 'files'),
                       (r'^admin[/]*$', 'admin'),
                       (r'^login[/]*$', 'login', {'SSL': True}),
                       (r'^logout[/]*$', 'logout'),
                       (r'^wslogin[/]*$', 'wslogin', {'SSL': True}),
                       (r'^wslogout[/]*$', 'wslogout'),
                       (r'^exception[/]*$', 'exception_view'))

# dispatch to either webservice, admin or general
urlpatterns += patterns('yabi.yabi.views',
                        (r'^ws/', include('yabi.yabi.wsurls'), {'SSL': True}),
                        (r'^engine/', include('yabi.yabiengine.urls')),
                        url(r'^status_page[/]*$', 'status_page', name='status_page'),
                        (r'^admin-pane/', include('yabi.yabi.adminurls'), {'SSL': True}),
                        (r'^admin-pane/', include(admin.site.urls), {'SSL': True}))

urlpatterns += patterns('yabi.yabi.views',
                        (r'^djcelery-admin/', include(djangoadmin.site.urls), {'SSL': True}))

# redirect / to /admin
urlpatterns += patterns('',
                        ('^$', RedirectView.as_view(url=urlresolvers.reverse('admin:index'))))
# pattern for serving statically
# not needed by runserver, but it is by gunicorn
# will be overridden by apache alias under WSGI
if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve',
                                {'document_root': settings.STATIC_ROOT, 'show_indexes': True}))

urlpatterns += patterns('',
                        (r'^favicon\.ico', RedirectView.as_view(url='/static/images/favicon.ico')))

urlpatterns += patterns('',
                        url(r'^djamboloader/', include('djamboloader.urls')))
