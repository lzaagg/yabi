from yabiadmin.yabi.UploadStreamer import UploadStreamer
#from yabiadmin.yabiengine.backendhelper import make_hmac
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from urlparse import urlparse
from urllib import quote
import json
from django.conf import settings

from yaphc import Http, PostRequest, UnauthorizedError
#from yabiadmin.yabiengine.backendhelper import BackendRefusedConnection, BackendHostUnreachable, PermissionDenied, FileNotFound, BackendStatusCodeError
from yabiadmin.yabiengine.backendhelper import get_fs_backendcredential_for_uri
from yabiadmin.decorators import authentication_required
from yabiadmin.backend import backend

import logging
logger = logging.getLogger(__name__)


#
# Our upload streamer
#
class FileUploadStreamer(UploadStreamer):
    def __init__(self, host, port, selector, cookies, fields):
        UploadStreamer.__init__(self)
        self._host = host
        self._port = port
        self._selector = selector
        self._fields = fields
        self._cookies = cookies

    def receive_data_chunk(self, raw_data, start):
        logger.debug('{0} {1}'.format(len(raw_data), start))
        return self.file_data(raw_data)

    def file_complete(self, file_size):
        """individual file upload complete"""
        logger.info("Streaming through of file %s has been completed. %d bytes have been transferred." % (self._present_file, file_size))
        return self.end_file()

    def new_file(self, field_name, file_name, content_type, content_length, charset):
        """beginning of new file in upload"""
        logger.debug('{0} {1} {2} {3} {4}'.format(field_name, file_name, content_type, content_length, charset))
        return UploadStreamer.new_file(self,file_name)

    def upload_complete(self):
        """all files completely uploaded"""
        logger.debug('')
        return self.end_connection()

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding):
        """raw input"""
        logger.debug('')
        # this is called right at the beginning. So we grab the uri detail here and initialise the outgoing POST
        self.post_multipart(host=self._host, port=self._port, selector=self._selector, cookies=self._cookies )


@authentication_required
def xput(request):
    """
    Uploads a file to the supplied URI
    """
    assert False, "TODO"
#    import socket
#    import httplib
#
#    yabiusername = request.user.username
#
#    try:
#        logger.debug("uri: %s" %(request.GET['uri']))
#        uri = request.GET['uri']
#
#        bc = get_fs_backendcredential_for_uri(yabiusername, uri)
#        decrypt_cred = bc.credential.get()
#        resource = "%s?uri=%s" % (settings.YABIBACKEND_PUT, quote(uri))
#
#        # TODO: the following is using GET parameters to push the decrypt creds onto the backend. This will probably make them show up in the backend logs
#        # we should push them via POST parameters, or at least not log them in the backend.
#        resource += "&username=%s&password=%s&cert=%s&key=%s"%(quote(decrypt_cred['username']),quote(decrypt_cred['password']),quote( decrypt_cred['cert']),quote(decrypt_cred['key']))
#
#        streamer = FileUploadStreamer(host=settings.BACKEND_IP, port=settings.BACKEND_PORT or 80, selector=resource, cookies=[], fields=[])
#        request.upload_handlers = [ streamer ]
#
#        # evaluating POST triggers the processing of the request body
#        request.POST
#
#        result=streamer.stream.getresponse()
#
#        content=result.read()
#        status=int(result.status)
#        reason = result.reason
#
#        response = {
#            "level":"success" if status==200 else "failure",
#            "message":content
#            }
#        return HttpResponse(content=json.dumps(response))
#
#    except BackendRefusedConnection, e:
#        return JsonMessageResponseNotFound(BACKEND_REFUSED_CONNECTION_MESSAGE)
#    except socket.error, e:
#        logger.critical("Error connecting to %s: %s" % (settings.YABIBACKEND_SERVER, e))
#        raise
#    except httplib.CannotSendRequest, e:
#        logger.critical("Error connecting to %s: %s" % (settings.YABIBACKEND_SERVER, e.message))
#        raise
#    except UnauthorizedError, e:
#        logger.critical("Unauthorized Error connecting to %s: %s. Is the HMAC set correctly?" % (settings.YABIBACKEND_SERVER, e.message))
#        raise


# TODO duplicated from ws views
@authentication_required
def put(request):
    """
    Uploads a file to the supplied URI
    """
    yabiusername = request.user.username

    logger.debug("uri: %s" %(request.GET['uri']))
    uri = request.GET['uri']

    files = []
    for key, f in request.FILES.items():
        logger.debug('handling file {0}'.format(key))
        upload_handle = backend.put_file(yabiusername, f.name, uri)
        for chunk in f.chunks():
            upload_handle.write(chunk)
        upload_handle.close()

    response = {
        "level":"success",
        "message": 'no message'
    }
    return HttpResponse(content=json.dumps(response))
