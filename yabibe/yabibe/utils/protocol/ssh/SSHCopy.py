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
"""Implement scp connections"""

import os
import sys

from FifoPool import Fifos

from BaseShell import BaseShell
from SSHRun import SSHExecProcessProtocolParamiko

from conf import config

DEBUG = False


class SCPError(Exception):
    pass


class SSHCopy(BaseShell):
    scp = os.path.join(os.path.dirname(os.path.realpath(__file__)), "paramiko-ssh.py")
    python = sys.executable

    def WriteToRemote(self, certfile, remoteurl, port=None, password="", fifo=None):
        subenv = self._make_env()
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])

        port = port or 22

        if not fifo:
            fifo = Fifos.Get()

        remoteuserhost, remotepath = remoteurl.split(':', 1)
        remoteuser, remotehost = remoteuserhost.split('@', 1)

        command = [self.python, self.scp]
        command += ["-i", certfile] if certfile else []
        command += ["-p", password] if password else []
        command += ["-u", remoteuser] if remoteuser else []
        command += ["-H", remotehost] if remotehost else []
        command += ["-l", fifo, "-r", remotepath]

        if DEBUG:
            print "CERTFILE", certfile
            print "REMOTEUSER", remoteuser
            print "REMOTEHOST", remotehost
            print "REMOTEPATH", remotepath
            print "PORT", port
            print "PASSWORD", "*" * len(password)
            print "FIFO", fifo

            print "COMMAND", command

        return BaseShell.execute(self, SSHExecProcessProtocolParamiko(), command, subenv), fifo

    def ReadFromRemote(self, certfile, remoteurl, port=None, password="", fifo=None):
        subenv = self._make_env()
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])

        port = port or 22

        if not fifo:
            fifo = Fifos.Get()

        remoteuserhost, remotepath = remoteurl.split(':', 1)
        remoteuser, remotehost = remoteuserhost.split('@', 1)

        command = [self.python, self.scp]
        command += ["-i", certfile] if certfile else []
        command += ["-p", password] if password else []
        command += ["-u", remoteuser] if remoteuser else []
        command += ["-H", remotehost] if remotehost else []
        command += ["-L", fifo, "-R", remotepath]

        if DEBUG:
            print "CERTFILE", certfile
            print "REMOTEUSER", remoteuser
            print "REMOTEHOST", remotehost
            print "REMOTEPATH", remotepath
            print "PORT", port
            print "PASSWORD", "*" * len(password)
            print "FIFO", fifo

            print "COMMAND", command

        return BaseShell.execute(self, SSHExecProcessProtocolParamiko(), command, subenv), fifo

    def WriteCompressedToRemote(self, certfile, remoteurl, port=None, password="", fifo=None):
        subenv = self._make_env()
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])

        port = port or 22

        if not fifo:
            fifo = Fifos.Get()

        remoteuserhost, remotepath = remoteurl.split(':', 1)
        remoteuser, remotehost = remoteuserhost.split('@', 1)

        path, filename = os.path.split(remotepath)
        print "REMOTEPATH", path, "===", filename

        command = [self.python, self.scp]
        command += ["-i", certfile] if certfile else []
        command += ["-p", password] if password else []
        command += ["-u", remoteuser] if remoteuser else []
        command += ["-H", remotehost] if remotehost else []
        command += ["-x", 'tar --gzip --extract --directory "%s"' % (path)]
        command += ["-I", fifo]

        if DEBUG:
            print "CERTFILE", certfile
            print "REMOTEUSER", remoteuser
            print "REMOTEHOST", remotehost
            print "REMOTEPATH", remotepath
            print "PORT", port
            print "PASSWORD", "*" * len(password)
            print "FIFO", fifo

            print "COMMAND", command

        return BaseShell.execute(self, SSHExecProcessProtocolParamiko(), command, subenv), fifo

    def ReadCompressedFromRemote(self, certfile, remoteurl, port=None, password="", fifo=None):
        subenv = self._make_env()
        subenv['YABIADMIN'] = config.yabiadmin
        subenv['HMAC'] = config.config['backend']['hmackey']
        subenv['SSL_CERT_CHECK'] = str(config.config['backend']['admin_cert_check'])

        port = port or 22

        if not fifo:
            fifo = Fifos.Get()

        remoteuserhost, remotepath = remoteurl.split(':', 1)
        remoteuser, remotehost = remoteuserhost.split('@', 1)

        path, filename = os.path.split(remotepath)
        print "REMOTEPATH", path, "=====", filename

        command = [self.python, self.scp]
        command += ["-i", certfile] if certfile else []
        command += ["-p", password] if password else []
        command += ["-u", remoteuser] if remoteuser else []
        command += ["-H", remotehost] if remotehost else []
        command += ["-x", 'tar --gzip --directory "%s" --create "%s"' % (path, filename if filename else ".")]
        command += ["-O", fifo]
        command += ["-N"]

        if DEBUG:
            print "CERTFILE", certfile
            print "REMOTEUSER", remoteuser
            print "REMOTEHOST", remotehost
            print "REMOTEPATH", remotepath
            print "PORT", port
            print "PASSWORD", "*" * len(password)
            print "FIFO", fifo

            print "COMMAND", command

        return BaseShell.execute(self, SSHExecProcessProtocolParamiko(), command, subenv), fifo
