# -*- coding: utf-8 -*-
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
# -*- coding: utf-8 -*-
import copy
import json
import os
import uuid
from datetime import datetime
from django.db import transaction
from django.http import HttpResponse
from yabiadmin.yabi import models
from yabiadmin.backend.celerytasks import process_workflow
from yabiadmin.yabiengine.enginemodels import EngineWorkflow
from yabiadmin.backend import backend
from yabiadmin.decorators import authentication_required
from collections import namedtuple
import logging
from six.moves import filter
logger = logging.getLogger(__name__)


class YabiError(Exception):
    pass


class ParsingError(YabiError):
    pass


@authentication_required
def is_stagein_required(request):
    logger.debug(request.user.username)
    try:
        _, params = extract_tools_and_params(request)
        input_files = [p.original_value for p in params if p.input_file]
        if input_files:
            resp = {'success': True, 'stagein_required': True, 'files': input_files}
        else:
            resp = {'success': True, 'stagein_required': False}
    except YabiError as e:
        resp = {'success': False, 'msg': str(e)}

    return HttpResponse(json.dumps(resp))


@authentication_required
@transaction.commit_manually
def submitjob(request):
    logger.debug(request.user.username)

    # TODO extract common code from here and submitworkflow

    try:
        tools, params = extract_tools_and_params(request)
        if len(tools) > 1:
            raise YabiError('Tool runs on more than one backend. '
                            'Specify one with --backend. '
                            'To list backends use "yabish backends".')
        tool = tools[0]
        job = create_job(tool, params)
        selectfile_job, job = split_job(job)
        workflow_dict = create_wrapper_workflow(selectfile_job, job, tool.desc.name)
        workflow_json = json.dumps(workflow_dict)
        user = models.User.objects.get(name=request.user.username)

        workflow = EngineWorkflow(name=workflow_dict["name"], user=user, json=workflow_json, original_json=workflow_json)
        workflow.save()

        # always commit transactions before sending tasks depending on state from the current transaction
        # http://docs.celeryq.org/en/latest/userguide/tasks.html
        transaction.commit()
        resp = {'success': True, 'workflow_id': workflow.id}

        # process workflow via celery
        process_workflow(workflow.pk).apply_async()
    except YabiError as e:
        transaction.rollback()
        logger.exception("Error in submitjob()")
        # TODO error returns success???
        resp = {'success': False, 'msg': str(e)}
    except Exception:
        transaction.rollback()
        logger.exception("Error in submitjob()")
        raise

    return HttpResponse(json.dumps(resp))


def split_job(job):
    '''Creates a selectfile job for any job that has input files'''
    files = []
    changed_job = copy.copy(job)
    params = []
    for param in job['parameterList']['parameter']:
        if type(param['value'][0]) == dict and param['value'][0].get('type') == 'file':
            filename = param['value'][0]['filename']
            value = {"jobId": 1}
            if filename:
                value['filename'] = filename
                value['type'] = "jobfile"
            else:
                value['type'] = "job"
            params.append({
                "valid": True,
                "value": [value],
                "switchName": param['switchName']
            })
            files.append(param['value'][0])
        else:
            params.append(param)

    changed_job['parameterList']['parameter'] = params

    if not files:
        selectfile_job = None
    else:
        tool = models.Tool.objects.get(desc__name="fileselector",
                                       backend__name="nullbackend")
        selectfile_job = {
            'valid': True,
            'toolName': 'fileselector',
            'toolId': tool.id,
            'parameterList': {
                'parameter': [{
                    'valid': True,
                    'value': files,
                    'switchName': 'files'}]
            }
        }
    return selectfile_job, changed_job


@authentication_required
def createstageindir(request):
    logger.debug(request.user.username)
    try:
        guid = request.REQUEST['uuid']
        dirs_to_create = [p[1] for p in request.REQUEST.items() if p[0].startswith('dir_')]
        uuid.UUID(guid)  # validation
        user = models.User.objects.get(name=request.user.username)

        stageindir = '%s%s/' % (user.default_stagein, guid)

        backend.mkdir(user.name, stageindir)
        for d in dirs_to_create:
            backend.mkdir(user.name, stageindir + '/' + d)

        resp = {'success': True, 'uri': stageindir}
    except Exception as e:
        resp = {'success': False, 'msg': str(e)}

    return HttpResponse(json.dumps(resp))


@authentication_required
def list_backends(request):
    q = {"credential__user__user__username": request.user.username}
    creds = models.BackendCredential.objects.filter(**q)
    backends = models.Backend.objects.exclude(name="nullbackend")
    # fixme: how to exclude fs backends?
    backends = backends.filter(id__in=creds.values_list("backend", flat=True))

    return HttpResponse(json.dumps({
        'success': True,
        'backends': list(backends.values("name", "description")),
    }), content_type="application/json")


# Implementation

ParsedArg = namedtuple('ParsedArg', 'name original_arg value original_value input_file')


class ParamDef(object):

    def __init__(self, name, switch_use, mandatory, is_input_file):
        self.name = name
        self.switch_use = switch_use
        self.mandatory = mandatory
        self.input_file = is_input_file
        self.value = None
        self.original_arg = None

    def matches(self, argument):
        if self.name == argument:
            self.original_arg = argument
            return True
        if self.switch_use in ('combined', 'combined with equals'):
            if argument.startswith(self.name):
                value_start = len(self.name)
                if self.switch_use == 'combined with equals':
                    value_start += 1
                self.value = [argument[value_start:]]
                self.original_arg = argument
                self.original_value = self.value[0]
                return True
        return False

    def consume_values(self, arguments):
        '''WARNING! This changes the passed in arguments list in place! '''
        if self.switch_use not in ('combined', 'combined with equals'):
            self.original_value = None
        if self.switch_use == 'switchOnly':
            self.value = ['Yes']
            return
        if self.switch_use == 'pair':
            if len(arguments) <= 1:
                raise ParsingError('Option %s requires 2 arguments' % self.name)
            v1 = arguments.pop(0)
            v2 = arguments.pop(0)
            if is_option(v1) and is_option(v2):
                raise ParsingError('Option %s requires 2 arguments' % self.name)
            self.value = [v1, v2]
            self.original_value = '%s %s' % (v1, v2)

        if self.switch_use not in ('combined', 'combined with equals'):
            if not arguments:
                raise ParsingError('Option %s requires an argument' % self.name)
            v = arguments.pop(0)
            if is_option(v):
                raise ParsingError('Option %s requires an argument' % self.name)
            self.value = [v]
            self.original_value = v
            if self.original_arg is None:
                self.original_arg = v

    def parsed_argument(self):
        value = self.value
        if self.input_file:
            root, filename = os.path.split(self.value[0])
            if not root.endswith('/'):
                root += '/'
            value = [{
                'path': [],
                'type': 'file',
                'root': root,
                'filename': filename,
                'pathComponents': [root]
            }]
        return ParsedArg(name=self.name, original_arg=self.original_arg,
                         value=value, original_value=self.original_value, input_file=self.input_file)


class YabiArgumentParser(object):
    def __init__(self, tool):
        self.paramdefs = self.init_paramdefs(tool)
        self.positional_paramdefs = list(filter(lambda x: x.switch_use == 'valueOnly', self.paramdefs))

    def parse_args(self, arguments):
        arguments_copy = copy.copy(arguments)
        parsed_options, unhandled_args = self.parse_options(arguments_copy)

        # Error if any unhandled argument are options (ie. start with '-' or '--')
        unknown_options = list(filter(lambda arg: is_option(arg), [arg[0] for arg in unhandled_args]))
        if unknown_options:
            raise ParsingError('Unknown option: %s' % ','.join(unknown_options))

        # All unhandled arguments have to be positional arguments
        if len(unhandled_args) != len(self.positional_paramdefs):
            pos_param_names = ', '.join([p.name for p in self.positional_paramdefs])
            raise ParsingError('Tool expects %d positional arguments (%s) but %d (%s) were passed in.' %
                               (len(self.positional_paramdefs), pos_param_names,
                                len(unhandled_args), ', '.join([arg[0] for arg in unhandled_args])))

        parsed_positionals = self.parse_positionals([arg[0] for arg in unhandled_args])
        result = self.combine_results(parsed_options, parsed_positionals, unhandled_args)
        self.validate_mandatory(result)

        return result

    # Implementation

    def init_paramdefs(self, tool):
        return [ParamDef(param.switch, param.switch_use.display_text, param.mandatory, param.input_file)
                for param in tool.toolparameter_set.all().order_by('rank')]

    def parse_options(self, arguments):
        remaining_args = arguments
        unhandled_args = []
        parsed_options = []

        last_arg = None
        while remaining_args:
            next_arg = remaining_args.pop(0)
            paramdef = self.find_matching_paramdef(next_arg)
            if paramdef:
                paramdef.consume_values(remaining_args)
                parsed_options.append(paramdef.parsed_argument())
            else:
                unhandled_args.append((next_arg, last_arg))
            last_arg = next_arg
        return parsed_options, unhandled_args

    def parse_positionals(self, unhandled_args):
        positionals = []
        for pos_paramdef in self.positional_paramdefs:
            pos_paramdef.consume_values(unhandled_args)
            positionals.append(pos_paramdef.parsed_argument())
        return positionals

    def combine_results(self, parsed_options, parsed_positionals, positional_order):
        # Start with the options ...
        result = copy.copy(parsed_options)
        # and insert the positionals at the right location based on the original order
        for positional in parsed_positionals:
            insert_after = find_item(positional_order,
                                     lambda x: x[0] == positional.original_arg)[1]
            insert_idx = 0
            if insert_after is not None:
                insert_idx = item_index(result, lambda x: x.original_arg == insert_after) + 1
            result.insert(insert_idx, positional)
        return result

    def find_matching_paramdef(self, arg):
        for paramdef in self.paramdefs:
            if paramdef.matches(arg):
                return paramdef

    def validate_mandatory(self, result):
        mandatory_params = [p.name for p in self.paramdefs if p.mandatory]
        missing_params = [p for p in mandatory_params if p not in [arg[0] for arg in result]]
        if missing_params:
            raise ParsingError('Mandatory option: %s not passed in.' % ','.join(missing_params))


def get_tool_from_request(username, post):
    toolname = post.get('name')
    backendname = post.get('backend', None) or None
    tooldesc = models.ToolDesc.objects.filter(name=toolname,
                                              toolgrouping__tool_set__users__name=username)[:1]

    if len(tooldesc) > 0:
        tooldesc = tooldesc[0]
        tools = tooldesc.tool_set.all()

        if backendname:
            # Select the tool for the given backend. Supports searching
            # for all backends starting with a string. If more than one
            # backend matches (not useful), then do an exact match instead.
            tools = tools.filter(backend__name__istartswith=backendname)
            if tools.count() > 1:
                tools = tools.filter(backend__name__iexact=backendname)

            if len(tools) == 0:
                raise YabiError("Tool \"%s\" doesn't exist on "
                                "backend \"%s\"" % (toolname, backendname))
        elif len(tools) == 0:
            raise YabiError('Unknown tool "%s"' % toolname)
    else:
        raise YabiError('Unknown tool name "%s"' % toolname)

    return tooldesc, tools


def extract_tools_and_params(request):
    tooldesc, tools = get_tool_from_request(request.user.username, request.POST)

    argparser = YabiArgumentParser(tooldesc)
    params = create_params(request, argparser)

    return tools, params


def create_job(tool, params):
    params_list = [{'switchName': arg.name, 'valid': True, 'value': arg.value}
                   for arg in params]
    return {'toolName': tool.desc.name, 'toolId': tool.id, 'valid': True,
            'parameterList': {'parameter': params_list}}


def create_wrapper_workflow(selectfile_job, job, toolname):
    def generate_name(toolname):
        return '%s (%s)' % (toolname, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    jobs = list(filter(lambda x: x is not None, [selectfile_job, job]))
    for i, job in enumerate(jobs):
        job['jobId'] = i + 1

    workflow = {
        'name': generate_name(toolname),
        # TODO this doesn't seem to be picked up
        'tags': ['yabish'],
        'jobs': jobs
    }

    return workflow


def create_params(request, argparser):
    arguments = reconstruct_argument_list(request)
    parsed_arguments = argparser.parse_args(arguments)
    return parsed_arguments


def reconstruct_argument_list(request):
    '''Reconstructs the argument list from request params named arg0, arg1, ... argN'''
    def argNtoN(argN):
        return int(argN[3:])
    arg_params = [(argNtoN(p[0]), p[1]) for p in request.POST.items() if p[0].startswith('arg')]
    arg_params.sort(cmp=lambda x, y: cmp(x[0], y[0]))
    arguments = [a[1] for a in arg_params]
    return arguments


def find_item(l, func):
    for item in l:
        if func(item):
            return item


def item_index(l, func):
    for i, item in enumerate(l):
        if func(item):
            return i


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def is_option(s):
    return s.startswith('-') and not is_int(s)
