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
from yabiadmin.backend.fsbackend import FSBackend
from yabiadmin.backend.exceptions import NotSupportedError, RetryException
from yabiadmin.backend.utils import get_credential_data, partition
from yabiadmin.yabiengine.urihelper import uriparse
import logging
import traceback
import boto
from functools import partial
from itertools import ifilter
import dateutil.parser
import threading
from io import BytesIO
from itertools import ifilterfalse


logger = logging.getLogger(__name__)


NEVER_A_SYMLINK = False
DELIMITER = '/'

ERROR_STATUS = -1
OK_STATUS = 0


class S3Backend(FSBackend):

    def __init__(self, *args, **kwargs):
        FSBackend.__init__(self, *args, **kwargs)
        self._bucket = None

    def bucket(self, name=None):
        if self._bucket is None:
            if name is None:
                raise ValueError("bucket not initialised")
            self._bucket = self.connect_to_bucket(name)
        return self._bucket

    def fifo_to_remote(self, uri, fifo_name, queue=None):
        thread = threading.Thread(target=self.upload_file, args=(uri, fifo_name, queue))
        thread.start()
        return thread

    def remote_to_fifo(self, uri, fifo_name, queue=None):
        thread = threading.Thread(target=self.download_file, args=(uri, fifo_name, queue))
        thread.start()
        return thread


    def is_item_matching_name(self, name, item):
        """We want to eliminate key names starting with the same prefix,
           but include keys at the next level (but not deeper) for dirs.
           Ex: listing for 'a'
               'a' included
               'abc' ignored
               'a/anything' included
               'a/anything/deeper' ignored"""
        name_and_delimiter = name + DELIMITER if not name.endswith(DELIMITER) else name
        def no_more_delimiters(item):
            item_name_end = item.name.rstrip(DELIMITER)[len(name_and_delimiter):]
            return DELIMITER not in item_name_end

        return (item.name == name or
                item.name.startswith(name_and_delimiter) and no_more_delimiters(item))

    def ls(self, uri):
        self.set_cred(uri)
        bucket_name, path = self.parse_s3_uri(uri)

        is_empty_key_for_dir = lambda k: k.name == path.lstrip(DELIMITER) and k.name.endswith(DELIMITER)
        is_item_matching_name = partial(self.is_item_matching_name, path.lstrip(DELIMITER))

        def filter_clause(item):
            return is_item_matching_name(item) and not is_empty_key_for_dir(item)

        try:
            bucket = self.bucket(bucket_name)
            keys_and_prefixes = ifilter(
                    filter_clause,
                    bucket.get_all_keys(prefix=path.lstrip(DELIMITER),
                    delimiter=DELIMITER))

            # Keys correspond to files, prefixes to directories
            keys, prefixes = partition(lambda k: type(k) == boto.s3.key.Key, keys_and_prefixes)

            files = [(basename(k.name), k.size, format_iso8601_date(k.last_modified), NEVER_A_SYMLINK) for k in keys]
            dirs = [(basename(p.name), 0, None, NEVER_A_SYMLINK) for p in prefixes]

            # Called on a directory with URI not ending in DELIMITER
            # We call ourself again correctly
            if len(files) == 0 and len(dirs) == 1 and not uri.endswith(DELIMITER):
                return self.ls(uri + DELIMITER)

        except boto.exception.S3ResponseError as e:
            logger.exception("Couldn't get listing from S3:")
            # TODO doing the same as SFTPBackend, but is this what we want?
            # This code is not executed by Celery tasks
            raise RetryException(e, traceback.format_exc())

        return {path: {
            'files': files,
            'directories': dirs
        }}

    def rm(self, uri):
        bucket_name, path = self.parse_s3_uri(uri)

        try:
            bucket = self.bucket(bucket_name)
            all_keys = self.get_keys_recurse(bucket, path)

            multi_delete_result = bucket.delete_keys(all_keys)
            if multi_delete_result.errors:
                # Some keys couldn't be deleted
                raise RuntimeError(
                    "The following keys couldn't be deleted when deleting uri %s: %s",
                    uri, ", ".join(multi_delete_result.errors))

        except Exception as exc:
            logger.exception("Error while trying to S3 rm uri %s", uri)
            raise RetryException(exc, traceback.format_exc())

    def mkdir(self, uri):
        self.set_cred(uri)
        dir_uri = uri if uri.endswith(DELIMITER) else uri + DELIMITER
        self.rm(dir_uri)
        bucket_name, path = self.parse_s3_uri(dir_uri)

        try:
            bucket = self.bucket()
            key = bucket.new_key(path.lstrip(DELIMITER))
            key.set_contents_from_string('')

        except Exception as exc:
            logger.exception("Error while trying to S3 rm uri %s", uri)
            raise RetryException(exc, traceback.format_exc())

    def local_copy(self, source, destination):
        raise NotSupportedError()

    def symbolic_link(self, source, destination):
        raise NotSupportedError()

    # Implementation

    def parse_s3_uri(self, uri):
        if uri.endswith(DELIMITER):
            uri = uri.rstrip(DELIMITER) + DELIMITER
        scheme, parts = uriparse(uri)
        bucket_name = parts.hostname.split('.')[0]
        path = parts.path

        return bucket_name, path

    def connect_to_bucket(self, bucket_name):
        aws_access_key_id, aws_secret_access_key = self.get_access_keys()
        connection = boto.connect_s3(aws_access_key_id, aws_secret_access_key)

        return connection.get_bucket(bucket_name)

    def get_access_keys(self):
        _, aws_access_key_id, aws_secret_access_key, _ = get_credential_data(self.cred.credential)
        return aws_access_key_id, aws_secret_access_key

    def download_file(self, uri, filename, queue=None):
        try:
            if queue is None:
                queue = NullQueue()
            bucket_name, path = self.parse_s3_uri(uri)

            bucket = self.connect_to_bucket(bucket_name)
            key = bucket.get_key(path.lstrip(DELIMITER))

            key.get_contents_to_filename(filename)

            queue.put(OK_STATUS)
        except:
            logger.exception("Exception thrown while S3 downloading %s to %s", uri, filename)
            queue.put(ERROR_STATUS)

    def upload_file(self, uri, filename, queue=None):
        try:
            if queue is None:
                queue = NullQueue()
            logger.debug("upload_file %s to %s", filename, uri)
            bucket_name, path = self.parse_s3_uri(uri)

            bucket = self.connect_to_bucket(bucket_name)

            CHUNKSIZE = 5 * 1024 * 1024
            # 5MB is the minimum size of a part when doing multipart uploads
            # Therefore, multipart uploads will fail if your file is smaller than 5MB

            with open(filename, 'rb') as f:
                data = f.read(CHUNKSIZE)
                if len(data) < CHUNKSIZE:
                    # File is smaller than CHUNKSIZE, upload in one go (ie. no multipart)
                    key = bucket.new_key(path.lstrip(DELIMITER))
                    size = key.set_contents_from_file(BytesIO(data))
                    logger.debug("Set %s bytes to %s", size, key.name)
                else:
                    # File is larger than CHUNKSIZE, there will be more parts so initiate
                    # the multipart_upload and upload in parts
                    multipart_upload = bucket.initiate_multipart_upload(path.lstrip(DELIMITER))
                    part_no = 1
                    while len(data) > 0:
                        multipart_upload.upload_part_from_file(BytesIO(data), part_no)
                        data = f.read(CHUNKSIZE)
                        part_no += 1

                    multipart_upload.complete_upload()
            queue.put(OK_STATUS)
        except:
            logger.exception("Exception thrown while S3 uploading %s to %s", filename, uri)
            queue.put(ERROR_STATUS)

    def get_keys_recurse(self, bucket, path):
        result = []

        is_item_matching_name = partial(self.is_item_matching_name, path.lstrip(DELIMITER))

        keys_and_prefixes = ifilter(
                is_item_matching_name,
                bucket.get_all_keys(prefix=path.lstrip(DELIMITER), delimiter=DELIMITER))

        # Keys correspond to files, prefixes to directories
        keys, prefixes = partition(lambda k: type(k) == boto.s3.key.Key, keys_and_prefixes)

        result.extend(keys)
        for p in prefixes:
            result.extend(self.get_keys_recurse(bucket, p.name))

        return result

    def parent_dir_uri(self, uri):
        uri = uri.rstrip(DELIMITER)
        return uri[:uri.rfind(DELIMITER)] + DELIMITER

    def path_exists(self, uri, bucket=None):
        if bucket is None:
            bucket = self.bucket()
        _, path = self.parse_s3_uri(uri)
        return bucket.get_key(path.lstrip(DELIMITER)) is not None


def basename(key_name, delimiter=DELIMITER):
    name = key_name.rstrip(delimiter)
    delimiter_last_position = name.rfind(delimiter)
    return name[delimiter_last_position + 1:]


def format_iso8601_date(iso8601_date):
    date = dateutil.parser.parse(iso8601_date)
    return date.strftime("%a, %d %b %Y %H:%M:%S")


class NullQueue(object):
    def put(self, value):
        pass
