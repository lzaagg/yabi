# -*- coding: utf-8 -*-
# Django settings for yabi project.
import os

if not os.environ.has_key('PROJECT_DIRECTORY'):
	os.environ['PROJECT_DIRECTORY']=os.path.dirname(__file__)
if not os.environ.has_key('SCRIPT_NAME'):								# this will be missing if we are running on the internal server
	os.environ['SCRIPT_NAME']=''
PROJECT_DIRECTORY = os.environ['PROJECT_DIRECTORY']
SCRIPT_NAME = os.environ['SCRIPT_NAME']

#import django.contrib.admin
from django.utils.webhelpers import url

DEBUG = True
TEMPLATE_DEBUG = DEBUG

#
# if we are deploying a DJANGODEV development version, we can override settings with environment variables
#
YABIBACKEND = os.environ["YABIBACKEND"] if "YABIBACKEND" in os.environ else "localhost.localdomain:8000/"
YABISTORE = os.environ["YABISTORE"] if "YABISTORE" in os.environ else "faramir.localdomain/yabistore/trunk"

# development deployment
if "DJANGODEV" in os.environ:
    DEBUG = True if os.path.exists(os.path.join(PROJECT_DIRECTORY,".debug")) else ("DJANGODEBUG" in os.environ)
    TEMPLATE_DEBUG = DEBUG
    DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    DATABASE_NAME = 'dev_yabmin'            # Or path to database file if using sqlite3.
    DATABASE_USER = 'yabminapp'             # Not used with sqlite3.
    DATABASE_PASSWORD = 'yabminapp'         # Not used with sqlite3.
    DATABASE_HOST = 'eowyn.localdomain'             # Set to empty string for localhost. Not used with sqlite3.
    DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
    SSL_ENABLED = False
    DEV_SERVER = True
    YABIBACKEND_SERVER, YABIBACKEND_BASE = YABIBACKEND.split("/",1)
    YABIBACKEND_BASE = "/" + YABIBACKEND_BASE                                   # NOT USED PRESENTLY
    assert YABIBACKEND_BASE=="/"
    
    YABISTORE_SERVER, YABISTORE_BASE = YABISTORE.split('/',1)
    YABISTORE_BASE = "/" + YABISTORE_BASE
    
    # debug site table
    SITE_ID = 1

elif "CUSTOMDB" in os.environ:
    DEBUG = True if os.path.exists(os.path.join(PROJECT_DIRECTORY,".debug")) else ("DJANGODEBUG" in os.environ)
    TEMPLATE_DEBUG = DEBUG
    DATABASE_ENGINE = os.environ['DATABASE_ENGINE']
    DATABASE_NAME = os.environ['DATABASE_NAME']
    DATABASE_USER = os.environ['DATABASE_USER']
    DATABASE_PASSWORD = os.environ['DATABASE_PASSWORD']
    DATABASE_HOST = os.environ['DATABASE_HOST']
    DATABASE_PORT = os.environ['DATABASE_PORT']
    
    SSL_ENABLED = False
    DEV_SERVER = True
    YABIBACKEND_SERVER, YABIBACKEND_BASE = YABIBACKEND.split("/",1)
    YABIBACKEND_BASE = "/" + YABIBACKEND_BASE                                   # NOT USED PRESENTLY
    assert YABIBACKEND_BASE=="/"
    
    YABISTORE_SERVER, YABISTORE_BASE = YABISTORE.split('/',1)
    YABISTORE_BASE = "/" + YABISTORE_BASE
    
    # debug site table
    SITE_ID = 1
    

# production deployment (probably using wsgi)
else:
    DEBUG = True if os.path.exists(os.path.join(PROJECT_DIRECTORY,".debug")) else ("DJANGODEBUG" in os.environ)
    TEMPLATE_DEBUG = DEBUG
    DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    DATABASE_NAME = 'dev_yabmin'            # Or path to database file if using sqlite3.
    DATABASE_USER = 'yabminapp'             # Not used with sqlite3.
    DATABASE_PASSWORD = 'yabminapp'         # Not used with sqlite3.
    DATABASE_HOST = 'eowyn.localdomain'             # Set to empty string for localhost. Not used with sqlite3.
    DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
    SSL_ENABLED = False
    DEV_SERVER = False
    YABIBACKEND_SERVER = 'boromir.localdomain:8000'
    YABISTORE_SERVER = "localhost.localdomain"
    YABISTORE_BASE = "/yabistore/trunk"
    
    # development site id
    SITE_ID = 1

print "DJANGODEV","DJANGODEV" in os.environ
print "DJANGODEBUG",DEBUG
for name in ['DATABASE_ENGINE','DATABASE_NAME','DATABASE_USER','DATABASE_PASSWORD','DATABASE_HOST','DATABASE_PORT']:
    if name in locals():
        print name,locals()[name]
     
print "YABISTORE",YABISTORE
print "YABISTORE_SERVER",YABISTORE_SERVER
print "YABISTORE_BASE",YABISTORE_BASE
print "YABIBACKEND",YABIBACKEND
print "YABIBACKEND_SERVER",YABIBACKEND_SERVER
print "YABIBACKEND_BASE",YABIBACKEND_BASE




YABIBACKEND_COPY = '/fs/copy'
YABIBACKEND_RCOPY = '/fs/rcopy'
YABIBACKEND_MKDIR = '/fs/mkdir'
YABIBACKEND_RM = '/fs/rm'
YABIBACKEND_LIST = '/fs/ls'
YABIBACKEND_PUT = '/fs/put'
YABIBACKEND_GET = '/fs/get'


# make sure that this is a tuple of tuples
ADMINS = (
    #('Tech Alerts', 'alerts@ccg.murdoch.edu.au'),
    ('Andrew Macgregor', 'andrew@ccg.murdoch.edu.au'),    
)

LOGIN_URL = "/login"

# so we can request /ws/tool/23 or /ws/tool/23/ and not get a 301 redirect
APPEND_SLASH = False

MANAGERS = ADMINS

# email server
EMAIL_HOST = 'ccg.murdoch.edu.au'
EMAIL_APP_NAME = "Yabi Admin"
SERVER_EMAIL = "apache@ccg.murdoch.edu.au"
EMAIL_SUBJECT_PREFIX = "Yabi Admin %s %s:"%("DEBUG" if DEBUG else "","DEV_SERVER" if DEV_SERVER else "")

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Australia/Perth'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_DIRECTORY,"static","media")

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = '/static/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = url('/static/admin-media/')

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'is(8wp-_s)lzw-xu=ogh3^+d&b+$fe73&3@8l5n-6-*d(_l-6z'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.email.EmailExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.ssl.SSLRedirect'
)
#MIDDLEWARE_CLASSES += ('yabmin.middleware.Logging',)

# our session cookie name (set to be different to admin)
SESSION_COOKIE_NAME = "yabiadmincookie"

ROOT_URLCONF = 'yabiadmin.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_DIRECTORY,"templates"),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    #'django_evolution',
    'yabiadmin.yabmin',
    'yabiadmin.yabiengine'
)

##
## Auth settings
##
AUTH_LDAP_SERVER = 'ldaps://fds2.localdomain'
AUTH_LDAP_SERVERS = (
    'ldaps://fds1.localdomain', 
    'ldaps://fds2.localdomain', 
    'ldaps://fds3.localdomain',
)
AUTH_LDAP_USER_BASE = 'ou=People,dc=ccg,dc=murdoch,dc=edu,dc=au'
AUTH_LDAP_GROUP_BASE = 'ou=Yabi,ou=Web Groups,dc=ccg,dc=murdoch,dc=edu,dc=au'
AUTH_LDAP_ADMIN_GROUP = 'admin'
AUTH_LDAP_GROUP = 'admin' # only admin users should be able to log in
AUTH_LDAP_USER_GROUP = 'yabi'

DEFAULT_GROUP = "baseuser"


# a directory that will be writable by the webserver, for storing various files...
WRITABLE_DIRECTORY = os.path.join(PROJECT_DIRECTORY,"scratch")

# Captcha image directory
CAPTCHA_IMAGES = os.path.join(WRITABLE_DIRECTORY, "captcha")

##
## Mako settings stuff
##

# extra mako temlate directories
MAKO_TEMPLATE_DIRS = ( os.path.join(PROJECT_DIRECTORY,"templates"), )

# mako compiled templates directory
MAKO_MODULE_DIR = os.path.join(WRITABLE_DIRECTORY, "templates")

# mako module name
MAKO_MODULENAME_CALLABLE = ''

##
## memcache server list
##
MEMCACHE_SERVERS = ['memcache1.localdomain:11211','memcache2.localdomain:11211']
MEMCACHE_KEYSPACE = ""

##
## CAPTCHA settings
##
# the filesystem space to write the captchas into
CAPTCHA_ROOT = os.path.join(MEDIA_ROOT, 'captchas')

# the URL base that points to that directory served out
CAPTCHA_URL = os.path.join(MEDIA_URL, 'captchas')

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.LDAPBackend',
#    'django.contrib.auth.backends.ModelBackend',
)

# for local development, this is set to the static serving directory. For deployment use Apache Alias
STATIC_SERVER_PATH = os.path.join(PROJECT_DIRECTORY,"static")

# status settings that can be used on workflow, job and task
STATUS = {'pending':'pending',
          'ready':'ready',
          'requested':'requested',
          'complete':'complete',
          'error':'error'
          }

##
## Logging setup
##
NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL = 0, 10, 20, 30, 40, 50
#import logging
LOG_DIRECTORY = os.path.join(PROJECT_DIRECTORY,"logs")
LOGGING_LEVEL = DEBUG
#LOGGING_LEVEL = logging.DEBUG if DEBUG else logging.CRITICAL
#LOGGING_FORMATTER = '%(asctime)s:%(name)s:%(levelname)s:%(filename)s:%(lineno)s:%(funcName)s:%(message)s'
LOGGING_FORMATTER = "%(message)s"
LOGS = ['yabiengine','yabiadmin']


# TODO the file upload only handles files that are written to disk at them moment
# so this MUST be set to 0
FILE_UPLOAD_MAX_MEMORY_SIZE = 0
