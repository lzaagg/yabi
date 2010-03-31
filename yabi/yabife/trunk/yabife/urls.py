import os
from django.conf.urls.defaults import *

urlpatterns = patterns('yabife.yabifeapp.views',
    (r'^(?P<url>ws/.*)$', 'adminproxy'),
    (r'^(?P<url>workflows/.*)$', 'storeproxy'),                       
	(r'^[/]*$', 'design'),
    (r'^design/reuse/(?P<id>.*)[/]*$', 'design'),
	(r'^design[/]*$', 'design'),
	(r'^jobs[/]*$', 'jobs'),
    (r'^files[/]*$', 'files'),
	(r'^menu[/]*$', 'menu'),
    (r'^login[/]*$', 'login', {'SSL':True}),
    (r'^logout[/]*$', 'logout')
)


# pattern for serving statically
# will be overridden by apache alias under WSGI
urlpatterns += patterns('',
    (r'^static/(?P<path>.*)$',
                        'django.views.static.serve', 
                        {'document_root': os.path.join(os.path.dirname(__file__),"static"), 'show_indexes': True}),

)

urlpatterns += patterns('django.views.generic.simple',
    (r'^favicon\.ico', 'redirect_to', {'url': '/static/images/favicon.ico'}),
)
