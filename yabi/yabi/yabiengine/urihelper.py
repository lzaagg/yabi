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
from urlparse import urlparse
import logging
from functools import reduce
logger = logging.getLogger(__name__)

import re
re_url_schema = re.compile(r'\w+')


def uriparse(uri):
    """
    This function returns a tuple containing the scheme and the ParseResult object.
    It is done this way as urlparse only accepts a specific list of url schemes
    and yabi:// is not one of them. The ParseResult object is read-only so
    we cannot inject the scheme back into it.
    A copy of this function is in yabi-sh.
    """
    try:
        scheme, rest = uri.split(":", 1)
        assert re_url_schema.match(scheme)
        return (scheme, urlparse(rest))
    except ValueError as e:
        logger.critical("%s - ValueError for uri: %s" % ("urihelper.uriparse", uri))
        logger.critical("%s - %s" % ("urihelper.uriparse", e.message))
        raise
    except AttributeError as e:
        logger.critical("%s - AttributeError for uri: %s" % ("urihelper.uriparse", uri))
        logger.critical("%s - %s" % ("urihelper.uriparse", e.message))
        raise


def uriunparse(scheme, hostname, username, path='/', port=None):
    if port:
        uri = "%s://%s@%s:%s%s" % (scheme, username, hostname, port, path)
    else:
        uri = "%s://%s@%s%s" % (scheme, username, hostname, path)
    return uri


def url_join(*args):
    '''This is used to join subpaths to already constructed urls'''
    return reduce(lambda a, b: a + b if a.endswith('/') else a + '/' + b, args)


def get_backend_userdir(backendcredential, yabiusername):
    """
    Supplies the front end with a list of backend uris including the user's home dir
    """
    logger.debug('Backendcredential: %s' % backendcredential)

    from yabi.yabi.models import BackendCredential
    from urlparse import urlunparse
    assert isinstance(backendcredential, BackendCredential)

    # check for the things vital to building a uri
    if not backendcredential.backend.hostname:
        raise Exception('No backend hostname for backend: %s' % backendcredential.backend)
    if not backendcredential.backend.scheme:
        raise Exception('No backend scheme for backend: %s' % backendcredential.backend)

    netloc = "%s@%s" % (backendcredential.credential.username, backendcredential.backend.hostname)
    if backendcredential.backend.port:
        netloc += ':%d' % backendcredential.backend.port

    path = backendcredential.backend.path + backendcredential.homedir

    return urlunparse((backendcredential.backend.scheme, netloc, path, '', '', ''))


def is_same_location(uri, other_uri):
    uri_scheme, uri_rest = uriparse(uri)
    other_scheme, other_rest = uriparse(other_uri)
    return (uri_scheme == other_scheme and uri_rest.hostname == other_rest.hostname and uri_rest.port == other_rest.port)
