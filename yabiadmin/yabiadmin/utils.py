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
from django.utils import simplejson as json
from django.conf import settings
from django.utils.encoding import smart_str

def json_error(message):
    if type(message) is str:
        return json.dumps({'error':message})
    
    import traceback
    return json.dumps({'error':traceback.format_exc()})


def using_dev_settings():
    
    using_dev_settings = False

    # these should be true in production
    for s in ['SSL_ENABLED', 'SESSION_COOKIE_SECURE', 'SESSION_COOKIE_HTTPONLY', ]:
        if getattr(settings, s) == False:
            using_dev_settings = True
            break

    # these should be false in production
    for s in ['DEBUG']:
        if getattr(settings, s) == True:
            using_dev_settings = True
            break

    # SECRET_KEY
    if settings.SECRET_KEY == 'set_this':
        using_dev_settings = True

    # HMAC_KEY
    if settings.HMAC_KEY == 'set_this':
        using_dev_settings = True

    return using_dev_settings

def detect_rdbms():
    assert(settings.DATABASES.has_key('default'))
    assert(settings.DATABASES['default'].has_key('ENGINE'))
    mapping = {
            'django.db.backends.postgresql_psycopg2': 'postgres',
            'django.db.backends.mysql': 'mysql',
            'django.db.backends.sqlite3': 'sqlite',
    }
    return mapping.get(settings.DATABASES['default']['ENGINE'], 'unknown')

def cache_keyname(key):
    """return a safe cache key"""
    # smart_str takes care of non-ascii characters (memcache doesn't support Unicode in keys)
    # memcache also doesn't like spaces
    return smart_str(key).replace(' ', '_')


