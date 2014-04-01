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
from django.utils import simplejson as json
from yabiadmin.backend.exceptions import RetryException, FileNotFoundError
from yabiadmin.backend.utils import create_fifo
from yabiadmin.backend.backend import fs_credential
from yabiadmin.backend.basebackend import BaseBackend
from yabiadmin.backend.pooling import get_ssh_pool_manager
from yabiadmin.yabiengine.urihelper import url_join, uriparse, is_same_location
from yabiadmin.constants import ENVVAR_FILENAME
import dateutil
import logging
import traceback
import shutil
import Queue
from six.moves import map
logger = logging.getLogger(__name__)


CP_PATH = '/bin/cp'


def stream_watcher(identifier, stream):

    # TODO
    # Can we pass through a ref to the process?
    # Can we unlink the fifo after read/write is done?
    # change to process_watcher and have one thread per process?
    for line in stream:
        logger.warning('{0} {1}'.format(identifier, line))

    if not stream.closed:
        stream.close()


class FSBackend(BaseBackend):

    @staticmethod
    def create_backend_for_scheme(fsscheme):
        backend = None

        if fsscheme == 'sftp' or fsscheme == 'scp':
            from yabiadmin.backend.sftpbackend import SFTPBackend
            backend = SFTPBackend()

        elif fsscheme == 'file' or fsscheme == 'localfs':
            from yabiadmin.backend.filebackend import FileBackend
            backend = FileBackend()

        elif fsscheme == 'select' or fsscheme == 'null':
            from yabiadmin.backend.selectfilebackend import SelectFileBackend
            backend = SelectFileBackend()

        elif fsscheme == 's3':
            from yabiadmin.backend.s3backend import S3Backend
            backend = S3Backend()

        return backend

    @staticmethod
    def factory(task):
        assert(task)
        assert(task.fsscheme)

        backend = FSBackend.create_backend_for_scheme(task.fsscheme)
        if backend is None:
            raise Exception('No valid scheme ({0}) is defined for task {1}'.format(task.fsscheme, task.id))

        backend.task = task
        backend.yabiusername = task.job.workflow.user.name
        return backend

    @staticmethod
    def urifactory(yabiusername, uri):
        assert(uri)
        fsscheme, fsbackend_parts = uriparse(uri)

        backend = FSBackend.create_backend_for_scheme(fsscheme)
        if backend is None:
            raise Exception("No backend can be found for uri %s with fsscheme %s for user %s" % (uri, fsscheme, yabiusername))

        backend.yabiusername = yabiusername
        backend.cred = fs_credential(yabiusername, uri)
        return backend

    @staticmethod
    def remote_copy(yabiusername, src_uri, dst_uri):
        FSBackend.remote_copy_recurse(yabiusername, src_uri, dst_uri)
        get_ssh_pool_manager().release()

    @staticmethod
    def remote_copy_recurse(yabiusername, src_uri, dst_uri):
        """Recursively copy src_uri to dst_uri"""
        logger.info('remote_copy {0} -> {1}'.format(src_uri, dst_uri))
        src_backend = FSBackend.urifactory(yabiusername, src_uri)
        dst_backend = FSBackend.urifactory(yabiusername, dst_uri)

        try:
            src_stat = src_backend.remote_uri_stat(src_uri)

            listing = src_backend.ls(src_uri)  # get _flat_ listing here not recursive as before
            dst_backend.mkdir(dst_uri)
            logger.debug("listing of src_uri %s = %s" % (src_uri, listing))
            for key in listing:
                # copy files using a fifo
                for listing_file in listing[key]['files']:
                    src_file_uri = url_join(src_uri, listing_file[0])
                    dst_file_uri = url_join(dst_uri, listing_file[0])
                    logger.debug("src_file_uri = %s" % src_file_uri)
                    logger.debug("dst_file_uri = %s" % dst_file_uri)
                    FSBackend.remote_file_copy(yabiusername, src_file_uri, dst_file_uri)

                # recurse on directories

                for listing_dir in listing[key]['directories']:
                    src_dir_uri = url_join(src_uri, listing_dir[0])
                    dst_dir_uri = url_join(dst_uri, listing_dir[0])
                    logger.debug("src_dir_uri = %s" % src_dir_uri)
                    logger.debug("dst_dir_uri = %s" % dst_dir_uri)
                    FSBackend.remote_copy_recurse(yabiusername, src_dir_uri, dst_dir_uri)

            if src_stat and src_backend.basename(src_uri.rstrip('/')) == dst_backend.basename(dst_uri.rstrip('/')):
                # Avoid setting the times if we're copying the contents of the source
                atime = src_stat.get('atime')
                mtime = src_stat.get('mtime')
                dst_backend.set_remote_uri_times(dst_uri, atime, mtime)
        except Exception as exc:
            raise RetryException(exc, traceback.format_exc())

    @staticmethod
    def remote_file_copy(yabiusername, src_uri, dst_uri):
        """Use a local fifo to copy a single file from src_uri to dst_uri"""
        logger.debug('remote_file_copy {0} -> {1}'.format(src_uri, dst_uri))

        # we need refs to the src and dst backends
        src_backend = FSBackend.urifactory(yabiusername, src_uri)
        dst_backend = FSBackend.urifactory(yabiusername, dst_uri)
        src_scheme, src_parts = uriparse(src_uri)
        dst_scheme, dst_parts = uriparse(dst_uri)
        # Making sure dst_uri is always a file not a dir
        if dst_parts.path.endswith("/"):  # Looks like a dir
            dst_file_uri = "%s/%s" % (dst_uri, src_backend.basename(src_parts.path))
            dst_scheme, dst_parts = uriparse(dst_uri)
        else:
            dst_file_uri = dst_uri

        fifo = None
        try:
            src_stat = src_backend.remote_uri_stat(src_uri)

            # create a fifo, start the write to/read from fifo
            fifo = create_fifo('remote_file_copy_' + yabiusername + '_' + src_parts.hostname + '_' + dst_parts.hostname)
            src_queue = Queue.Queue()
            dst_queue = Queue.Queue()
            src_cmd = src_backend.remote_to_fifo(src_uri, fifo, src_queue)
            dst_cmd = dst_backend.fifo_to_remote(dst_file_uri, fifo, dst_queue)
            src_cmd.join()
            dst_cmd.join()
            src_status = src_queue.get()
            dst_status = dst_queue.get()

            # check exit status
            if src_status != 0:
                raise RetryException('remote_file_copy remote_to_fifo failed')
            if dst_status != 0:
                raise RetryException('remote_file_copy fifo_to_remote failed')

            if src_stat:
                atime = src_stat.get('atime')
                mtime = src_stat.get('mtime')
                dst_backend.set_remote_uri_times(dst_file_uri, atime, mtime)

        except Exception as exc:
            raise RetryException(exc, traceback.format_exc())

    @staticmethod
    def remote_file_download(yabiusername, uri):
        """Use a local fifo to download a remote file"""
        logger.debug('{0} -> local fifo'.format(uri))

        # we need ref to the backend
        backend = FSBackend.urifactory(yabiusername, uri)
        scheme, parts = uriparse(uri)
        try:
            # create a fifo, start the write to/read from fifo
            fifo = create_fifo('remote_file_download_' + yabiusername + '_' + parts.hostname)
            thread = backend.remote_to_fifo(uri, fifo)

            # TODO some check on the copy thread

            return fifo
        except FileNotFoundError:
            raise
        except Exception as exc:
            raise RetryException(exc, traceback.format_exc())

    @staticmethod
    def remote_file_upload(yabiusername, filename, uri):
        """Use a local fifo to upload to a remote file"""
        logger.debug('local_fifo -> {0}'.format(uri))

        # we need ref to the backend
        backend = FSBackend.urifactory(yabiusername, uri)
        scheme, parts = uriparse(uri)

        # uri for an upload must specify filename. we can't rely on the
        # source name as we copy from a fifo with a random name
        if not uri.endswith(filename):
            if not uri.endswith('/'):
                uri = uri + '/'
            uri = uri + filename

        try:
            # create a fifo, start the write to/read from fifo
            fifo = create_fifo('remote_file_upload_' + yabiusername + '_' + parts.hostname)
            thread = backend.fifo_to_remote(uri, fifo)

            # TODO some check on the copy thread

            return fifo
        except Exception as exc:
            raise RetryException(exc, traceback.format_exc())

    def save_envvars(self, task, envvars_uri):
        try:
            fifo = FSBackend.remote_file_download(self.yabiusername, envvars_uri)
            with open(fifo) as f:
                content = f.read()
            envvars = json.loads(content)
        except:
            logger.exception("Could not read contents of envvars file '%s' for task %s", envvars_uri, task.pk)
        else:
            task.envvars_json = json.dumps(envvars)
            task.save()

    def stage_in_files(self):
        self.mkdir(self.working_dir_uri())
        self.mkdir(self.working_input_dir_uri())
        self.mkdir(self.working_output_dir_uri())
        self.create_local_remnants_dir()

        stageins = self.task.get_stageins()
        for stagein in stageins:
            self.stage_in(stagein)
            if stagein.matches_filename(ENVVAR_FILENAME):
                self.save_envvars(self.task, stagein.src)

    def stage_in(self, stagein):
        """Perform a single stage in."""
        logger.debug(stagein.method)

        if stagein.method == 'copy':
            if stagein.src.endswith('/'):
                return FSBackend.remote_copy(self.yabiusername, stagein.src, stagein.dst)
            else:
                return FSBackend.remote_file_copy(self.yabiusername, stagein.src, stagein.dst)

        if stagein.method == 'lcopy':
            return self.local_copy(stagein.src, stagein.dst)

        if stagein.method == 'link':
            dst = stagein.dst
            if stagein.src.endswith('/'):
                dst = stagein.dst + os.path.basename(stagein.src[:-1])
            return self.symbolic_link(stagein.src, dst)

    def stage_out_files(self):
        """
        Stage out files from fs backend to stageout area.
        Also upload any local remnants of the task to the stageout area
        """
        # first we need a stage out directory
        backend_for_stageout = FSBackend.urifactory(self.yabiusername, self.task.stageout)
        backend_for_stageout.mkdir(self.task.stageout)

        # deal with any remanants from local commands
        self.stage_out_local_remnants()

        # now the stageout proper
        method = self.task.job.preferred_stageout_method
        logger.debug('stage out method is {0}'.format(method))
        if method == 'lcopy':
            if is_same_location(self.working_output_dir_uri(), self.task.stageout):
                return self.local_copy_recursive(self.working_output_dir_uri(), self.task.stageout)
            else:
                method = 'copy'

        if method == 'copy':
            return FSBackend.remote_copy(self.yabiusername, self.working_output_dir_uri(), self.task.stageout)

        raise RuntimeError("Invalid stageout method %s for task %s" % (method, self.task.pk))

    def stage_out_local_remnants(self):
        """
        stage out any local remanants
        some tasks/backends will leave remnants (STDERR/STDOUT) locally so we
        need to upload them to the stageout area
        """
        logger.debug('stage_out_local_remnants from {0}'.format(self.local_remnants_dir()))
        logger.debug('stage_out_local_remnants to {0}'.format(self.task.stageout))
        # stage out local remnants
        remnants_dir = self.local_remnants_dir()
        for (dirpath, dirnames, filenames) in os.walk(remnants_dir):
            for filename in filenames:
                # get a fifo to remote file
                uri = url_join(self.task.stageout, dirpath[len(remnants_dir):])
                logger.debug('uploading {0} to {1}'.format(filename, uri))
                upload_as_fifo = FSBackend.remote_file_upload(self.yabiusername, filename, uri)
                # write our remnant to the fifo
                remnant = os.path.join(dirpath, filename)
                #process = execute([CP_PATH, remnant, upload_as_fifo])
                #status = process.wait()

                try:
                    #shutil.copyfileobj(open(remnant, 'r'), open(upload_as_fifo, 'w+'))
                    shutil.copyfileobj(open(remnant, 'r'), open(upload_as_fifo, 'w'))
                except Exception as exc:
                    logger.error('copy to upload fifo failed')
                    raise RetryException(exc, traceback.format_exc())

                # check exit status
                #if status != 0:
                #    # TODO logger.error will fail with unicode errors
                #    logger.debug(str(process.stdout.read()))
                #    logger.debug(str(process.stderr.read()))
                #    raise RetryException('copy to upload fifo failed')

                #if os.path.exists(upload_as_fifo):
                #    os.unlink(upload_as_fifo)

            for dirname in dirnames:
                # any directories we encounter we create in the stageout area
                os.path.join(dirpath, dirname)
                uri = url_join(self.task.stageout, dirpath[len(remnants_dir):], dirname)
                self.mkdir(uri)

    # TODO review later: maybe this should be static method or similar
    # feels strange we create the FSBackend with a factory based on task but then
    # we need to create another backend for the working_dir
    def clean_up_task(self):
        # remove working directory
        working_dir_backend = FSBackend.urifactory(self.yabiusername, self.working_dir_uri())
        working_dir_backend.rm(self.working_dir_uri())
        # remove local remnants directory
        shutil.rmtree(self.local_remnants_dir())

    def ls_recursive(self, uri):
        result = self.ls(uri)

        dirs = []
        if result.values():
            dirs = result.values()[0].get('directories')

        dir_uris = map(lambda d: "%s/%s" % (uri.rstrip("/"), d[0].lstrip("/")), dirs)
        for d in dir_uris:
            result.update(self.ls_recursive(d))
        return result

    def set_cred(self, uri):
        from yabiadmin.backend.backend import fs_credential
        self.cred = fs_credential(self.yabiusername, uri)

    def basename(self, path):
        return os.path.basename(path)

    def remote_to_fifo(self, uri, fifo):
        raise NotImplementedError("")

    def fifo_to_remote(self, uri, fifo):
        raise NotImplementedError("")

    def remote_uri_stat(self, uri):
        return {}

    def set_remote_uri_times(self, uri, atime, mtime):
        pass

    def rm(self, uri):
        raise NotImplementedError("")

    def mkdir(self, uri):
        raise NotImplementedError("")

    def ls(self, uri):
        raise NotImplementedError("")

    def local_copy(self, source, destination):
        raise NotImplementedError("")

    def local_copy_recursive(self, source, destination):
        raise NotImplementedError("")

    def symbolic_link(self, source, destination):
        raise NotImplementedError("")

    @staticmethod
    def format_iso8601_date(iso8601_date):
        date = dateutil.parser.parse(iso8601_date)
        return date.strftime("%a, %d %b %Y %H:%M:%S")


class NullQueue(object):
    def put(self, value):
        pass
