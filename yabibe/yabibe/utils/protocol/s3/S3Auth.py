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

from utils.geventtools import GETFailure
from Exceptions import NoCredentials, AuthException
from conf import config
import urllib

DEBUG = False


class S3Auth(object):

    def AuthProxyUser(self, yabiusername, scheme, username, hostname, path, *args):
        """Auth a user via getting the credentials from the json yabiadmin backend. When the credentials are gathered, successcallback is called with the deferred.
        The deferred should be the result channel your result will go back down"""

        try:
            # remove prefixed '/'s from path
            while len(path) and path[0] == '/':
                path = path[1:]

            # get credential for uri...
            from TaskManager.TaskTools import UserCreds
            uri = "%s://%s@%s/%s" % (scheme, username, hostname, urllib.quote(path))
            credentials = UserCreds(yabiusername, uri, credtype="fs")

            assert 'key' in credentials and 'cert' in credentials and 'password' in credentials, "Malformed credential JSON received from admin. I received: %s" % (str(credentials))

            return credentials

        except GETFailure, gf:
            gf_message = gf.args[0]
            if gf_message[0] == -1 and "404" in gf_message[1]:
                # connection problems
                raise NoCredentials("User: %s does not have credentials for this user: %s backend: %s on host: %s\n" % (yabiusername, username, scheme, hostname))

            raise AuthException("Tried to get credentials from %s:%d and failed: %s" % (config.yabiadminserver, config.yabiadminport, gf_message[1]))
