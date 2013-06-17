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
from twistedweb2 import resource, http_headers, responsecode, http
from twisted.internet import defer
from utils.submit_helpers import parsePOSTDataRemoteWriter
import weakref
import os
import gevent
from TaskManager.TaskTools import Sleep, Copy, List, Mkdir, CopyError
from utils.parsers import parse_url
from utils.geventtools import GETFailure
from Exceptions import BlockingException
from connector.FSConnector import NotImplemented
import traceback
import signal

DEFAULT_RCOPY_PRIORITY = 1

DEBUG = False


class FileRCopyResource(resource.PostableResource):
    VERSION = 0.1
    maxMem = 100 * 1024
    maxFields = 16
    maxSize = 10 * 1024 * 102

    def __init__(self, request=None, path=None, fsresource=None):
        """Pass in the backends to be served out by this FSResource"""
        self.path = path

        if not fsresource:
            raise Exception("FileCopyResource must be informed on construction as to which FSResource is its parent")

        self.fsresource = weakref.ref(fsresource)

    def render(self, request):
        # break our request path into parts
        return http.Response(responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "request must be POST\n")

    #@hmac_authenticated
    def http_POST(self, request):
        """
        Respond to a POST request.
        Reads and parses the incoming body data then calls L{render}.

        @param request: the request to process.
        @return: an object adaptable to L{iweb.IResponse}.

        NOTE: parameters must be Content-Type: application/x-www-form-urlencoded
        eg.
        """
        #print "POST!",request

        deferred = parsePOSTDataRemoteWriter(request, self.maxMem, self.maxFields, self.maxSize)

        # Copy command
        def RCopyCommand(res):
            # source and destination
            if 'src' not in request.args or 'dst' not in request.args:
                return http.Response(responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "rcopy must specify source 'src' and destination 'dst'\n")

            # if 'contents' is set, then copy the contents of the source directory, not the directory itself (like going cp -r src/* dst/)
            copy_contents = 'contents' in request.args

            # override default priority
            priority = int(request.args['priority'][0]) if "priority" in request.args else DEFAULT_RCOPY_PRIORITY

            src = request.args['src'][0]
            dst = request.args['dst'][0]

            yabiusername = request.args['yabiusername'][0] if "yabiusername" in request.args else None

            if not yabiusername:
                return http.Response(responsecode.BAD_REQUEST, {'content-type': http_headers.MimeType('text', 'plain')}, "You must pass in a yabiusername so I can go get a credential.\n")

            if not dst.endswith('/'):
                dst += '/'

            # parse the source and dest uris
            src_scheme, src_address = parse_url(src)
            dst_scheme, dst_address = parse_url(dst)

            src_username = src_address.username
            dst_username = dst_address.username
            src_path, src_filename = os.path.split(src_address.path)
            dst_path, dst_filename = os.path.split(dst_address.path)
            src_hostname = src_address.hostname
            dst_hostname = dst_address.hostname
            src_port = src_address.port
            dst_port = dst_address.port

            # backends
            sbend = self.fsresource().GetBackend(src_scheme)
            dbend = self.fsresource().GetBackend(dst_scheme)

            #our http result channel. this stays open until the copy is finished
            result_channel = defer.Deferred()

            #
            # our top down tasklet to run
            #
            def rcopy_runner_thread():
                try:
                    ##
                    ## Try using zput/zget to do rcopy first
                    ##
                    try:
                        writeproto, fifo = dbend.GetCompressedWriteFifo(dst_hostname, dst_username, dst_path, dst_port, dst_filename, yabiusername=yabiusername)
                        readproto, fifo2 = sbend.GetCompressedReadFifo(src_hostname, src_username, src_path, src_port, src_filename, fifo, yabiusername=yabiusername)

                        def fifo_cleanup(response):
                            os.unlink(fifo)
                            return response
                        result_channel.addCallback(fifo_cleanup)

                    except BlockingException, be:
                        #sbend.unlock(locks[0])
                        #if locks[1]:
                            #dbend.unlock(locks[1])
                        print traceback.format_exc()
                        result_channel.callback(http.Response(responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(be)))
                        return

                    if DEBUG:
                        print "READ:", readproto, fifo2
                        print "WRITE:", writeproto, fifo

                    # wait for one to finish
                    while not readproto.isDone() and not writeproto.isDone():
                        gevent.sleep()

                    # if one died and not the other, then kill the non dead one
                    if readproto.isDone() and readproto.exitcode != 0 and not writeproto.isDone():
                        # readproto failed. write proto is still running. Kill it
                        if DEBUG:
                            print "READ FAILED", readproto.exitcode, writeproto.exitcode
                        print "read failed. attempting os.kill(", writeproto.transport.pid, ",", signal.SIGKILL, ")", type(writeproto.transport.pid), type(signal.SIGKILL)
                        while writeproto.transport.pid is None:
                            #print "writeproto transport pid not set. waiting for setting..."
                            gevent.sleep()
                        os.kill(writeproto.transport.pid, signal.SIGKILL)
                    else:
                        # wait for write to finish
                        if DEBUG:
                            print "WFW", readproto.exitcode, writeproto.exitcode
                        while writeproto.exitcode is None:
                            gevent.sleep()

                        # did write succeed?
                        if writeproto.exitcode == 0:
                            if DEBUG:
                                print "WFR", readproto.exitcode, writeproto.exitcode
                            while readproto.exitcode is None:
                                gevent.sleep()

                    if readproto.exitcode == 0 and writeproto.exitcode == 0:
                        if DEBUG:
                            print "Copy finished exit codes 0"
                            print "readproto:"
                            print "ERR:", readproto.err
                            print "OUT:", readproto.out
                            print "writeproto:"
                            print "ERR:", writeproto.err
                            print "OUT:", writeproto.out

                        result_channel.callback(http.Response(responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, "Copy OK\n"))
                        return
                    else:
                        rexit = "Killed" if readproto.exitcode is None else str(readproto.exitcode)
                        wexit = "Killed" if writeproto.exitcode is None else str(writeproto.exitcode)

                        msg = "Copy failed:\n\nRead process: " + rexit + "\n" + readproto.err + "\n\nWrite process: " + wexit + "\n" + writeproto.err + "\n"
                        #print "MSG",msg
                        result_channel.callback(http.Response(responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, msg))
                        return

                except NotImplemented, ni:
                    ##
                    ## Fallback to old manual rcopy
                    ##
                    print ni

                    # get a recursive listing of the source
                    try:
                        fsystem = List(path=src, recurse=True, yabiusername=yabiusername)
                    except BlockingException, be:
                        print traceback.format_exc()
                        result_channel.callback(http.Response(responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(be)))

                    # lets split the source path on separator
                    destination_dir_name = "" if copy_contents else ([X for X in src.split("/") if len(X)][-1] + '/')

                    # remember the directories we make so we only make them once
                    created = []

                    # count the files we copy
                    file_count = 0
                    folder_count = 0

                    for directory in sorted(fsystem.keys()):
                        # make directory
                        destpath = directory[len(src_path) + 1:]              # the subpath part
                        if len(destpath) and destpath[-1] != '/':
                            destpath += '/'
                        #print "D:",dst,":",destpath,";",src_path
                        if dst + destination_dir_name + destpath not in created:
                            #print dst+destination_dir_name+destpath,"not in",created
                            try:
                                Mkdir(dst + destination_dir_name + destpath, yabiusername=yabiusername)
                                folder_count += 1
                            except BlockingException, be:
                                print traceback.format_exc()
                                result_channel.callback(http.Response(responsecode.SERVICE_UNAVAILABLE,
                                                        {'content-type': http_headers.MimeType('text', 'plain')},
                                                        str(be)))
                            except GETFailure, gf:
                                # ignore. directory probably already exists
                                pass
                            created.append(dst + destination_dir_name + destpath)

                        for file, size, date, link in fsystem[directory]['files']:
                            if DEBUG:
                                print "COPY", file, size, date
                                print "EXTRA", ">", destpath, ">", directory
                            src_uri = src + destpath + file
                            dst_uri = dst + destination_dir_name + destpath + file

                            if DEBUG:
                                print "Copy(", src_uri, ",", dst_uri, ")"
                            #print "Copy(",sbend+directory+"/"+file,",",dst+destpath+'/'+file,")"
                            try:
                                Copy(src_uri, dst_uri, yabiusername=yabiusername, priority=priority)
                                file_count += 1
                            except CopyError, ce:
                                print "RCOPY: Continuing after failed copy %s => %s : %s" % (src_uri, dst_uri, str(ce))
                            Sleep(0.1)

                    result_channel.callback(http.Response(responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')},
                                            "%d files %d folders copied successfuly\n" % (file_count, folder_count)))
                except BlockingException, be:
                    print traceback.format_exc()
                    result_channel.callback(http.Response(responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(be)))
                except GETFailure, gf:
                    print traceback.format_exc()
                    if "503" in gf.message[1]:
                        result_channel.callback(http.Response(responsecode.SERVICE_UNAVAILABLE, {'content-type': http_headers.MimeType('text', 'plain')}, str(gf)))
                    else:
                        result_channel.callback(http.Response(responsecode.INTERNAL_SERVER_ERROR, {'content-type': http_headers.MimeType('text', 'plain')}, str(gf)))
                except Exception, e:
                    print traceback.format_exc()
                    result_channel.callback(http.Response(responsecode.INTERNAL_SERVER_ERROR,
                                            {'content-type': http_headers.MimeType('text', 'plain')},
                                            str(e)))
                    return

            gevent.spawn(rcopy_runner_thread)
            return result_channel

            #return http.Response(responsecode.OK, {'content-type': http_headers.MimeType('text', 'plain')}, "OK: %s\n" % res)

        deferred.addCallback(RCopyCommand)

        # save failed
        def save_failed(result):
            return http.Response(responsecode.INTERNAL_SERVER_ERROR,
                                 {'content-type': http_headers.MimeType('text', 'plain')},
                                 str(result))

        deferred.addErrback(save_failed)
        return deferred
