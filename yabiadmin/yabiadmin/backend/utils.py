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
import os
import datetime
import subprocess
import socket
from yabiadmin.yabiengine.urihelper import url_join
import traceback
from mako.template import Template
import paramiko
import logging
from yabiadmin.backend.exceptions import RetryException
import uuid
import StringIO
from yabiadmin import settings
from yabiadmin.crypto_utils import AESTEMP
logger = logging.getLogger(__name__)


def execute(args, bufsize=0, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, cwd=None, env=None):
    """execute a process and return a handle to the process"""
    status = None
    try:
        logger.debug(args)
        process = subprocess.Popen(args, bufsize=bufsize, stdin=stdin, stdout=stdout, stderr=stderr, shell=shell, cwd=cwd, env=env)
    except Exception, exc:
        logger.error(exc)
        raise RetryException(exc, traceback.format_exc())

    return process


def valid_filename(filename):
    """Ensure filenames for fifo are valid, trimmed to 100"""
    import string
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in filename if c in valid_chars)
    filename = filename[:100]
    return filename


def create_fifo(suffix='', dir='/tmp'):
    """make a fifo on the filesystem and return its path"""
    import uuid
    filename = 'yabi_fifo_' + str(uuid.uuid4()) + '_' + suffix
    filename = valid_filename(filename)
    filename = os.path.join(dir, filename)
    filename = str(filename)
    logger.debug('create_fifo {0}'.format(filename))
    os.umask(0)
    os.mkfifo(filename, 0600)
    return filename


def submission_script(template, working, command, modules, cpus, memory, walltime, yabiusername, username, host, queue, stdout, stderr, tasknum, tasktotal):
    """Mako templating support function for submission script templating."""
    cleaned_template = template.replace('\r\n', '\n').replace('\n\r', '\n').replace('\r', '\n')
    tmpl = Template(cleaned_template)

    # our variable space
    variables = {
        'working': working,
        'command': command,
        'modules': modules,
        'cpus': cpus,
        'memory': memory,
        'walltime': walltime,
        'yabiusername': yabiusername,
        'username': username,
        'host': host,
        'queue': queue,
        'stdout': stdout,
        'stderr': stderr,
        'tasknum': tasknum,
        'tasktotal': tasktotal,
        'arrayid': tasknum,
        'arraysize': tasktotal
    }

    return str(tmpl.render(**variables))


def get_host_key(hostname):
    """
    host key for hostname. Does not handle multiple keys for the same host
    Not being used. I dont think it worth implementing until Paramiko supports ECDSA keys
    """
    logger.debug('get_host_key {0}'.format(hostname))
    from yabiadmin.yabi.models import HostKey
    host_keys = HostKey.objects.filter(hostname=hostname).filter(allowed=True)
    for key in host_keys:
        logger.debug('{0} {1}'.format(key.key_type, key.data))
        return key.key_type, key.data
    return None, None


def harvest_host_key(hostname, port, username, password, pkey):
    """
    Attempt an ssh connection and extract the host key. Does not raise errors.
    Not being used. I dont think it worth implementing until Paramiko supports ECDSA keys
    """
    logger.debug('save_host_key {0}'.format(hostname))
    try:
        # connect to harvest the host key
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            pkey=pkey,
            key_filename=None,
            timeout=None,
            allow_agent=False,
            look_for_keys=True,
            compress=False,
            sock=None)

        keys = ssh.get_host_keys()
        logger.debug(keys.lookup(hostname))
        key_dict = keys.lookup(hostname)
        if key_dict is None:
            logger.error('No host key found for {0}'.format(hostname))
            return

        # process any host keys
        import binascii
        for key_type in key_dict.keys():
            fingerprint = binascii.hexlify(key_dict[key_type].get_fingerprint())
            data = key_dict[key_type].get_base64()
            logger.debug('{0} {1}'.format(fingerprint, data))

            # dont save duplicate entries
            from yabiadmin.yabi.models import HostKey
            if HostKey.objects.filter(hostname=hostname, key_type=key_type, fingerprint=fingerprint, data=data).count() == 1:
                continue

            # save the key
            host_keys = HostKey.objects.create(hostname=hostname, fingerprint=fingerprint, key_type=key_type, data=data)
    except Exception, exc:
        logger.error(exc)


def try_to_load_key_file(key_type, credential_key, passphrase=None):
    try:
        pkey = key_type.from_private_key(StringIO.StringIO(credential_key), passphrase)
        return pkey
    except paramiko.SSHException, sshex:
        # ignoring exceptions of form "not a valid (DSA|RSA) private key file"
        msg = str(sshex)
        if not (msg.startswith("not a valid") and msg.endswith("private key file")):
            logger.exception("SSHException caught:")
            raise

    return None


def create_paramiko_pkey(key, passphrase=None):
    pkey = (
        try_to_load_key_file(paramiko.RSAKey, key, passphrase) 
        or
        try_to_load_key_file(paramiko.DSSKey, key, passphrase))

    if pkey is None:
        raise paramiko.SSHException("Passed in key not supported. Supported keys are RSA and DSS")

    return pkey


def sshclient(hostname, port, credential):
    if port is None:
        port = 22
    ssh = None

    if credential.is_cached:
        decrypted_credential = credential.get()
        username = decrypted_credential['username']
        key = decrypted_credential['key']
        passphrase = decrypted_credential['password']
    elif credential.is_protected:
        credential.unprotect()
        username = credential.username
        key = credential.key
        passphrase = credential.password
    elif credential.is_encrypted:
        logger.debug("credential encrypted and not in cache?!")
    else:
        username = credential.username
        key = credential.key
        passphrase = credential.password



    logger.debug('Connecting to {0}@{1}:{2}'.format(username, hostname, port))

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()

        pkey = create_paramiko_pkey(key, passphrase)

        ssh.connect(
                hostname=hostname,
                port=port,
                username=username,
                pkey=pkey,
                key_filename=None,
                password=None,
                timeout=None,
                allow_agent=False,
                look_for_keys=False,
                compress=False,
                sock=None)

    except paramiko.BadHostKeyException, bhke:  # BadHostKeyException - if the server's host key could not be verified
        raise RetryException(bhke, traceback.format_exc())
    except paramiko.AuthenticationException, aue:  # AuthenticationException - if authentication failed
        raise RetryException(aue, traceback.format_exc())
    except paramiko.SSHException, sshe:  # SSHException - if there was any other error connecting or establishing an SSH session
        raise RetryException(sshe, traceback.format_exc())
    except socket.error, soe:  # socket.error - if a socket error occurred while connecting
        raise RetryException(soe, traceback.format_exc())

    return ssh

def _get_creation_date(file_path):
    """
    @param file_path:
    @return: Creation date as a string in format like "Jul 26 2013"
    """
    return datetime.datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%b %d %Y")

def ls(top_level_path,recurse=False):
    listing = {}

    def append_slash(path):
        if not path.endswith("/"):
            return path + "/"
        else:
            return path

    def info_tuple(root, name):
        file_path = os.path.join(root, name)
        is_a_link = os.path.islink(file_path)
        if is_a_link:
            size = os.lstat(file_path).st_size
        else:
            size = os.path.getsize(file_path)
        date_string = _get_creation_date(file_path)

        return name, size, date_string, is_a_link

    if os.path.isfile(top_level_path):
        parent_folder = os.path.dirname(top_level_path)
        file_name = os.path.basename(top_level_path)
        file_info = info_tuple(parent_folder, file_name)
        return {top_level_path: {"files": [file_info], "directories": []}}

    for root, directories, files in os.walk(top_level_path,topdown=True):
        slashed_root = append_slash(root)
        listing[slashed_root] = {}
        listing[slashed_root]['files'] = []
        for file_name in sorted(files):
                file_info_tuple = info_tuple(root, file_name)
                listing[slashed_root]['files'].append(file_info_tuple)

        listing[slashed_root]['directories'] = []
        for directory in sorted(directories):
            directory_info_tuple = info_tuple(root, directory)
            listing[slashed_root]['directories'].append(directory_info_tuple)

        if root == top_level_path and not recurse:
            return listing

    return listing












