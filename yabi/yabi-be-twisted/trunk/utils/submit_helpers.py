#
# support functions TODO: put in seperate file
#
import os.path, tempfile
from twisted.internet import defer
from twisted.web2 import http, iweb, fileupload, responsecode
from StringIO import StringIO
        
TMP_DIRECTORY="/tmp"
        
@defer.deferredGenerator
def parseMultipartFormData(stream, boundary,
            maxMem=100*1024, maxFields=1024, maxSize=10*1024*1024,basepath=TMP_DIRECTORY):
    # If the stream length is known to be too large upfront, abort immediately
    
    if stream.length is not None and stream.length > maxSize:
            raise fileupload.MimeFormatError("Maximum length of %d bytes exceeded." %
                                                            maxSize)
    
    mms = fileupload.MultipartMimeStream(stream, boundary)
    numFields = 0
    args = {}
    files = {}
    
    while 1:
        datas = mms.read()
        if isinstance(datas, defer.Deferred):
            datas = defer.waitForDeferred(datas)
            yield datas
            datas = datas.getResult()
        if datas is None:
            break
        
        numFields+=1
        if numFields == maxFields:
            raise fileupload.MimeFormatError("Maximum number of fields %d exceeded"%maxFields)
        
        # Parse data
        fieldname, filename, ctype, stream = datas
        if filename is None:
            # Not a file
            outfile = StringIO()
            maxBuf = min(maxSize, maxMem)
        else:
            #print "...->",fieldname, filename, ctype, stream 
            #outfile = tempfile.NamedTemporaryFile(prefix=basepath)
            outfile = open(os.path.join(basepath,filename),'wb')
            maxBuf = maxSize
        x = fileupload.readIntoFile(stream, outfile, maxBuf)
        if isinstance(x, defer.Deferred):
            x = defer.waitForDeferred(x)
            yield x
            x = x.getResult()
        if filename is None:
            # Is a normal form field
            outfile.seek(0)
            data = outfile.read()
            args.setdefault(fieldname, []).append(data)
            maxMem -= len(data)
            maxSize -= len(data)
        else:
            # Is a file upload
            maxSize -= outfile.tell()
            outfile.seek(0)
            outfile.close()
            files.setdefault(fieldname, []).append((filename, ctype, outfile))
        
        
    yield args, files
    return

def parsePOSTData(request, maxMem=100*1024, maxFields=1024,
                            maxSize=10*1024*1024,basepath="/tmp/tmp"):
    """
    Parse data of a POST request.

    @param request: the request to parse.
    @type request: L{twisted.web2.http.Request}.
    @param maxMem: maximum memory used during the parsing of the data.
    @type maxMem: C{int}
    @param maxFields: maximum number of form fields allowed.
    @type maxFields: C{int}
    @param maxSize: maximum size of file upload allowed.
    @type maxSize: C{int}

    @return: a deferred that will fire when the parsing is done. The deferred
            itself doesn't hold a return value, the request is modified directly.
    @rtype: C{defer.Deferred}
    """
    if request.stream.length == 0:
        return defer.succeed(None)

    parser = None
    ctype = request.headers.getHeader('content-type')

    if ctype is None:
        return defer.succeed(None)

    def updateArgs(data):
        args = data
        request.args.update(args)

    def updateArgsAndFiles(data):
        args, files = data
        request.args.update(args)
        request.files.update(files)

    def error(f):
        f.trap(fileupload.MimeFormatError)
        raise http.HTTPError(
            http.StatusResponse(responsecode.BAD_REQUEST, str(f.value)))

    if (ctype.mediaType == 'application'
        and ctype.mediaSubtype == 'x-www-form-urlencoded'):
        print "A"
        d = fileupload.parse_urlencoded(request.stream)
        d.addCallbacks(updateArgs, error)
        return d
    elif (ctype.mediaType == 'multipart'
        and ctype.mediaSubtype == 'form-data'):
        print "B"
        boundary = ctype.params.get('boundary')
        if boundary is None:
            return defer.fail(http.HTTPError(
                        http.StatusResponse(
                            responsecode.BAD_REQUEST,
                            "Boundary not specified in Content-Type.")))
        d = parseMultipartFormData(request.stream, boundary,
                            maxMem, maxFields, maxSize,basepath=basepath)
        d.addCallbacks(updateArgsAndFiles, error)
        return d
    else:
        print "C"
        return defer.fail(http.HTTPError(
            http.StatusResponse(
                responsecode.BAD_REQUEST,
                "Invalid content-type: %s/%s" % (
                    ctype.mediaType, ctype.mediaSubtype))))


from twisted.web2.stream import readStream
def parsePUTData(request, maxMem=100*1024, maxFields=1024,
                            maxSize=10*1024*1024,filename="/tmp/test.tmp"):
    """
    Parse data of a PUT request.

    @param request: the request to parse.
    @type request: L{twisted.web2.http.Request}.
    @param maxMem: maximum memory used during the parsing of the data.
    @type maxMem: C{int}
    @param maxFields: maximum number of form fields allowed.
    @type maxFields: C{int}
    @param maxSize: maximum size of file upload allowed.
    @type maxSize: C{int}

    @return: a deferred that will fire when the parsing is done. The deferred
            itself doesn't hold a return value, the request is modified directly.
    @rtype: C{defer.Deferred}
    """
    data = []
    
    def gotData(newdata):
        data+=newdata
        
    d = readStream(request.stream, gotData)
    
    def _finishedReading(ignore):
        # do something with data
        print "got",data
        
    d.addCallback(_finishedReading)
    return d

@defer.deferredGenerator
def parseMultipartFormDataWriter(stream, boundary,
            maxMem=100*1024, maxFields=1024, maxSize=10*1024*1024,writer=None):
    # If the stream length is known to be too large upfront, abort immediately
    
    if stream.length is not None and stream.length > maxSize:
            raise fileupload.MimeFormatError("Maximum length of %d bytes exceeded." %
                                                            maxSize)
    
    mms = fileupload.MultipartMimeStream(stream, boundary)
    numFields = 0
    args = {}
    files = {}
    
    while 1:
        datas = mms.read()
        if isinstance(datas, defer.Deferred):
            datas = defer.waitForDeferred(datas)
            yield datas
            datas = datas.getResult()
        if datas is None:
            break
        
        numFields+=1
        if numFields == maxFields:
            raise fileupload.MimeFormatError("Maximum number of fields %d exceeded"%maxFields)
        
        # Parse data
        fieldname, filename, ctype, stream = datas
        if filename is None:
            # Not a file
            outfile = StringIO()
            maxBuf = min(maxSize, maxMem)
        else:
            #print "...->",fieldname, filename, ctype, stream 
            #outfile = tempfile.NamedTemporaryFile(prefix=basepath)
            outfile = writer(filename)
            print "OUTFILE=",outfile
            if isinstance(outfile, defer.Deferred):
                #writer not ready yet.
                outfile = defer.waitForDeferred(outfile)
                yield outfile
                outfile = outfile.getResult()
                print "OUTFILE IS NOW",outfile
            maxBuf = maxSize
        print "calling fileupload.readIntoFile",outfile
        x = fileupload.readIntoFile(stream, outfile, maxBuf)
        print "returned",x
        if isinstance(x, defer.Deferred):
            x = defer.waitForDeferred(x)
            yield x
            x = x.getResult()
            print "now returned",x
        if filename is None:
            # Is a normal form field
            #outfile.seek(0)
            data = outfile.read()
            args.setdefault(fieldname, []).append(data)
            maxMem -= len(data)
            maxSize -= len(data)
        else:
            # Is a file upload
            #maxSize -= outfile.tell()
            #outfile.seek(0)
            print "file upload finished..."
            outfile.close()
            files.setdefault(fieldname, []).append((filename, ctype, outfile))
        
        
    yield args, files
    return


def parsePOSTDataRemoteWriter(request, maxMem=100*1024, maxFields=1024,
                            maxSize=10*1024*1024,writer=None):
    """
    Parse data of a POST request.

    @param request: the request to parse.
    @type request: L{twisted.web2.http.Request}.
    @param maxMem: maximum memory used during the parsing of the data.
    @type maxMem: C{int}
    @param maxFields: maximum number of form fields allowed.
    @type maxFields: C{int}
    @param maxSize: maximum size of file upload allowed.
    @type maxSize: C{int}

    @return: a deferred that will fire when the parsing is done. The deferred
            itself doesn't hold a return value, the request is modified directly.
    @rtype: C{defer.Deferred}
    """
    if request.stream.length == 0:
        return defer.succeed(None)

    parser = None
    ctype = request.headers.getHeader('content-type')

    if ctype is None:
        return defer.succeed(None)

    def updateArgs(data):
        #print "updateArgs",data
        args = data
        request.args.update(args)

    def updateArgsAndFiles(data):
        #print "updateArgsAndFiles",data
        args, files = data
        request.args.update(args)
        request.files.update(files)

    def error(f):
        f.trap(fileupload.MimeFormatError)
        print "POST Parse error:",f.value
        raise f

    if (ctype.mediaType == 'application'
        and ctype.mediaSubtype == 'x-www-form-urlencoded'):
        d = fileupload.parse_urlencoded(request.stream)
        d.addCallbacks(updateArgs, error)
        return d
    elif (ctype.mediaType == 'multipart'
        and ctype.mediaSubtype == 'form-data'):
        boundary = ctype.params.get('boundary')
        if boundary is None:
            return defer.fail(http.HTTPError(
                        http.StatusResponse(
                            responsecode.BAD_REQUEST,
                            "Boundary not specified in Content-Type.")))
        d = parseMultipartFormDataWriter(request.stream, boundary,
                            maxMem, maxFields, maxSize,writer=writer)
        d.addCallbacks(updateArgsAndFiles, error)
        return d
    else:
        return defer.fail(http.HTTPError(
            http.StatusResponse(
                responsecode.BAD_REQUEST,
                "Invalid content-type: %s/%s" % (
                    ctype.mediaType, ctype.mediaSubtype))))


