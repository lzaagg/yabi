# -*- coding: utf-8 -*-
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from yabiadmin.yabmin.models import User, ToolGrouping, ToolGroup, Tool, ToolParameter, Credential, Backend, ToolSet, BackendCredential
from django.utils import webhelpers
from django.utils import simplejson as json
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.conf import settings
from yabiadmin.yabiengine import wfbuilder
from yabiadmin.yabiengine.backendhelper import get_listing, get_backend_list, get_file, get_backendcredential_for_uri, copy_file, rm_file
from yabiadmin.security import validate_user, validate_uri
from yabiadmin.utils import json_error
import mimetypes
from urllib import quote


from yabmin.file_upload import *

from django.contrib import logging
logger = logging.getLogger('yabiadmin')

## TODO do we want to limit tools to those the user can access?
def tool(request, toolname):
    logger.debug('')

    try:
        tool = Tool.objects.get(name=toolname)
        return HttpResponse(tool.json())
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json_error("Object not found"))


@validate_user
def menu(request, *args, **kwargs):
    logger.debug('')

    username = kwargs["username"]
    
    try:
        toolsets = ToolSet.objects.filter(users__name=username)
        output = {"toolsets":[]}

        # add each toolset
        for toolset in toolsets:

            ts = {}
            output["toolsets"].append(ts)
            ts["name"] = toolset.name
            ts["toolgroups"] = []


            # make up a dict of toolgroups
            toolgroups = {}

            for toolgroup in ToolGrouping.objects.filter(tool_set=toolset):
                if not toolgroup.tool_group.name in toolgroups:
                    tg = {}
                    toolgroups[toolgroup.tool_group.name] = tg
                else:
                    tg = toolgroups[toolgroup.tool_group.name]

                if not "name" in tg:
                    tg["name"] = toolgroup.tool_group.name
                if not "tools" in tg:
                    tg["tools"] = []

                tool = {}
                tool["name"] = toolgroup.tool.name
                tool["displayName"] = toolgroup.tool.display_name
                tool["description"] = toolgroup.tool.description                
                tg["tools"].append(tool)
                tool["outputExtensions"] = toolgroup.tool.output_filetype_extensions()
                tool["inputExtensions"] = toolgroup.tool.input_filetype_extensions()


            # now add the toolgroups to toolsets
            for key, value in toolgroups.iteritems():
                ts["toolgroups"].append(value)


        return HttpResponse(json.dumps({"menu":output}))
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json_error("Object not found"))    


@validate_uri
def ls(request):
    """
    This function will return a list of backends the user has access to IF the uri is empty. If the uri
    is not empty then it will pass on the call to the backend to get a listing of that uri
    """
    logger.debug('')
    
    try:
        logger.debug("GET: %s " %request.GET['uri'])
        if request.GET['uri']:
            logger.debug("get_listing")
            filelisting = get_listing(request.GET['yabiusername'], request.GET['uri'])
        else:
            filelisting = get_backend_list(request.GET['yabiusername'])

        return HttpResponse(filelisting)
    except Exception, e:
        return HttpResponseNotFound(json_error(e))


@validate_uri
def copy(request):
    """
    This function will return a list of backends the user has access to IF the uri is empty. If the uri
    is not empty then it will pass on the call to the backend to get a listing of that uri
    """
    logger.debug('')
    
    try:
        logger.debug("Copy: %s -> %s " %(request.GET['src'],request.GET['dst']))
        status, data = copy_file(request.GET['yabiusername'],request.GET['src'],request.GET['dst'])

        return HttpResponse(content=data, status=status)
    except Exception, e:
        return HttpResponseNotFound(json_error(e))

@validate_uri
def rm(request):
    """
    This function will return a list of backends the user has access to IF the uri is empty. If the uri
    is not empty then it will pass on the call to the backend to get a listing of that uri
    """
    logger.debug('')
    
    try:
        logger.debug("Rm: %s" %(request.GET['uri']))
        status, data = rm_file(request.GET['yabiusername'],request.GET['uri'])

        return HttpResponse(content=data, status=status)
    except Exception, e:
        return HttpResponseNotFound(json_error(e))


@validate_uri
def get(request):
    """
    Returns the requested uri. get_file returns an httplib response wrapped in a FileIterWrapper. This can then be read
    by HttpResponse
    """
    logger.debug('')

    try:
        uri = request.GET['uri']
        yabiusername = request.GET['yabiusername']
        
        try:
            filename = uri.rsplit('/', 1)[1]
        except IndexError, e:
            logger.critical('Unable to get filename from uri: %s' % uri)
            filename = 'default.txt'

        logger.debug(uri)
        logger.debug(filename)

        response = HttpResponse(get_file(yabiusername, quote(uri)))

        type, encoding = mimetypes.guess_type(filename)
        if type is not None:
            response['content-type'] = type

        if encoding is not None:
            response['content-encoding'] = encoding

        response['content-disposition'] = 'attachment; filename=%s' % filename

        return response

    
    #return HttpResponse(get_file(request.GET['uri']))
#        return HttpResponse(open('/export/home/tech/macgregor/svn-devel/ccg/yabi/yabi-be-twisted/trunk/yabiadmin/alice.txt'))
##         response = HttpResponse(FileIterWrapper(open('/export/home/tech/macgregor/svn-devel/ccg/yabi/yabi-be-twisted/trunk/yabiadmin/alice.txt')))
##         response['Content-Disposition'] = 'attachment; filename=foo.xls'
##         return response


#        return HttpResponse(FileIterWrapper(open('/export/home/tech/macgregor/svn-devel/ccg/yabi/yabi-be-twisted/trunk/yabiadmin/alice.txt')))

    except Exception, e:
        return HttpResponseNotFound(json_error(e))


@validate_uri
def put(request):
    """
    Uploads a file to the supplied URI
    """
    logger.debug('')

    import socket
    import httplib

    try:
        uri = request.GET['uri']
        yabiusername = request.GET['yabiusername']
        
        resource = "%s?uri=%s" % (settings.YABIBACKEND_PUT, quote(uri))

        # TODO this only works with files written to disk by django
        # at the moment so the FILE_UPLOAD_MAX_MEMORY_SIZE must be set to 0
        # in settings.py
        files = []
        in_file = request.FILES['file1']
        files.append((in_file.name, in_file.name, in_file.temporary_file_path()))
        logger.debug(files)
        
        bc = get_backendcredential_for_uri(yabiusername, uri)
        #data = [('username', bc.credential.username),
                    #('password', bc.credential.password),
                    #('cert', bc.credential.cert),
                    #('key', bc.credential.key)]
        data=[]
        
        resource += "&username=%s&password=%s&cert=%s&key=%s"%(quote(bc.credential.username),quote(bc.credential.password),quote( bc.credential.cert),quote(bc.credential.key))
                    
        logger.debug("POSTing %s to %s -> %s"%(str(data),settings.YABIBACKEND_SERVER,resource))

        logger.debug("files:%s"%repr(files))

        h = post_multipart(settings.YABIBACKEND_SERVER, resource, data, files)
        return HttpResponse('ok')
        
    except socket.error, e:
        logger.critical("Error connecting to %s: %s" % (settings.YABIBACKEND_SERVER, e))
        raise
    except httplib.CannotSendRequest, e:
        logger.critical("Error connecting to %s: %s" % (settings.YABIBACKEND_SERVER, e.message))
        raise


@validate_user
def submitworkflow(request):
    logger.debug('')
    logger.debug("POST KEYS: %r"%request.POST.keys())
    
    # probably want to catch the type of exceptions we may get from this
    wfbuilder.build(request.POST['username'], request.POST["workflowjson"])
    
    return HttpResponse(request.POST["workflowjson"])

