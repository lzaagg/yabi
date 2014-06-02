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
from urllib import quote
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core import urlresolvers
from yabiadmin.yabi.models import *
from yabiadmin import ldaputils
from ccg_django_utils import webhelpers
from django.utils import simplejson as json
from django import forms
from django.views.debug import get_safe_settings
from django.contrib import messages
from django.conf import settings
import logging
import six

logger = logging.getLogger(__name__)


class AddToolForm(forms.Form):
    tool_json = forms.CharField(widget=forms.Textarea)

    def clean_tool_json(self):
        data = self.cleaned_data['tool_json']
        try:
            tool_dict = json.loads(data)
        except Exception:
            raise forms.ValidationError("Unable to load json. Please check it is valid.")

        if Tool.objects.filter(name=tool_dict["tool"]["name"]):
            raise forms.ValidationError("A tool named %s already exists." % tool_dict["tool"]["name"])

        return data


class ToolGroupView:
    def __init__(self, name):
        self.name = name
        self.tools = set([])

    def sorted_tools(self):
        logger.debug('')
        for tool in sorted(self.tools):
            yield tool


class ToolParamView:
    def __init__(self, tool_param):
        self._tool_param = tool_param
        self.rank = tool_param.rank is None and ' ' or tool_param.rank
        self.switch = tool_param.switch
        self.switch_use = tool_param.switch_use.display_text
        self.properties = self.other_properties()

    def other_properties(self):
        tp = self._tool_param
        props = []

        if tp.mandatory:
            props.append('Mandatory')
        if tp.file_assignment != 'none':
            props.append('Input File (%s)' % ",".join(
                ['"%s"' % af.name for af in tp.accepted_filetypes.all()]))
        if tp.output_file:
            props.append('Output File')
        if tp.use_output_filename:
            props.append('Use Output Filename: %s' % tp.use_output_filename)
        if tp.extension_param:
            props.append('Extension parameter: %s' % tp.extension_param.extension)
        if tp.batch_bundle_files:
            props.append('Bundle Files: %s' % tp.batch_bundle_files)
        if tp.hidden:
            props.append('Hidden')

        return props


def format_params(tool_parameters):
    for param in tool_parameters:
        yield ToolParamView(param)


@staff_member_required
def tool(request, tool_id):
    logger.debug("")

    tool = get_object_or_404(Tool, pk=tool_id)

    return render_to_response('yabi/tool.html', {
        'tool': tool,
        'user': request.user,
        'title': 'Tool Details',
        'root_path': urlresolvers.reverse('admin:index'),
        'edit_url': urlresolvers.reverse('admin:yabi_tool_change', args=(tool.id,)),
        'json_url': webhelpers.url('/ws/tool/' + quote(tool.name)),
        'tool_params': format_params(tool.toolparameter_set.order_by('id')),
    })


@staff_member_required
def modify_backend_by_id(request, id):
    """This is used primarily by test harness to modify backend settings mid test"""
    be = Backend.objects.get(id=id)
    for key, val in six.iteritems(request.REQUEST):
        logger.debug('{0}={1}'.format(key, val))
        setattr(be, key, None if val == "None" else val)
    be.save()

    return HttpResponse("OK")


@staff_member_required
def modify_backend_by_name(request, scheme, hostname):
    """This is used primarily by test harness to modify backend settings mid test"""
    be = Backend.objects.get(scheme=scheme, hostname=hostname)
    for key, val in six.iteritems(request.REQUEST):
        logger.debug('{0}={1}'.format(key, val))
        setattr(be, key, None if val == "None" else val)
    be.save()

    return HttpResponse("OK")


@staff_member_required
def user_tools(request, user_id):
    logger.debug('')
    tooluser = get_object_or_404(User, pk=user_id)
    tool_groupings = ToolGrouping.objects.filter(tool_set__users=tooluser)
    unique_tool_groups = {}
    for grouping in tool_groupings:
        tool_group_name = grouping.tool_group.name
        tool_name = grouping.tool.name
        tgv = unique_tool_groups.setdefault(tool_group_name, ToolGroupView(tool_group_name))
        tgv.tools.add(tool_name)

    return render_to_response("yabi/user_tools.html", {
        'user': request.user,
        'tooluser': tooluser,
        'title': 'Tool Listing',
        'root_path': urlresolvers.reverse('admin:index'),
        'tool_groups': sorted(unique_tool_groups.values(), key=lambda tgv: tgv.name)})


@staff_member_required
def user_backends(request, user_id):
    logger.debug('')
    backenduser = get_object_or_404(User, pk=user_id)

    becs = BackendCredential.objects.filter(credential__user=backenduser)

    return render_to_response("yabi/user_backends.html", {
        'user': request.user,
        'backenduser': backenduser,
        'title': 'Backend Listing',
        'root_path': urlresolvers.reverse('admin:index'),
        'backendcredentials': becs
    })


def register_users(request):
    """
    Take a list of names and add them to the Auth User table
    """
    logger.debug('')
    uids = request.POST.keys()

    for uid in uids:

        try:
            # save in auth user
            username = uid.replace('uid=', '')
            user, created = DjangoUser.objects.get_or_create(username=username)
            logger.debug("Django user %s for %s" % ("created" if created else 'already existed', username))

            # save in yabi user
            user, created = User.objects.get_or_create(name=username)
            logger.debug("Yabi user %s for %s" % ("created" if created else 'already existed', username))

        except Exception as e:
            logger.critical("Users not registered because of %s" % e)
            pass


@staff_member_required
def ldap_users(request):
    """
    Display a list of users in the Yabi ldap group that are not in database. Allow users to automatically add them to the database
    """
    logger.debug('')

    if not settings.LDAP_IN_USE:
        return render_to_response("yabi/ldap_not_in_use.html", {
            'user': request.user,
            'root_path': urlresolvers.reverse('admin:index'),
        })

    if request.method == 'POST':
        register_users(request)

    all_ldap_users = ldaputils.get_all_users()
    yabi_userids = ldaputils.get_yabi_userids()

    ldap_yabi_users = [ldaputils.format(entry[0], entry[1]) for entry in
                       all_ldap_users.items() if entry[0] in yabi_userids]

    db_user_names = [user.name for user in User.objects.all()]
    user_in_db = lambda u: u.uid in db_user_names

    existing_ldap_users = [user for user in ldap_yabi_users if user_in_db(user)]
    unexisting_ldap_users = [user for user in ldap_yabi_users if not user_in_db(user)]

    return render_to_response("yabi/ldap_users.html", {
        'user': request.user,
        'unexisting_ldap_users': unexisting_ldap_users,
        'existing_ldap_users': existing_ldap_users,
        'root_path': urlresolvers.reverse('admin:index'),
    })


@staff_member_required
def backend(request, backend_id):
    logger.debug('')
    backend = get_object_or_404(Backend, pk=backend_id)

    return render_to_response('yabi/backend.html', {
        'backend': backend,
        'user': request.user,
        'title': 'Backend Details',
        'root_path': urlresolvers.reverse('admin:index'),
    })


@staff_member_required
def backend_cred_test(request, backend_cred_id):
    logger.debug('')

    bec = get_object_or_404(BackendCredential, pk=backend_cred_id)

    from yabiadmin.yabiengine import backendhelper

    template_vars = {
        'bec': bec,
        'user': request.user,
        'title': 'Backend Credential Test',
        'root_path': urlresolvers.reverse('admin:index'),
        'listing': None,
        'error': None,
        'error_help': None
    }

    dict_join = lambda a, b: a.update(b) or a

    try:
        rawdata = backendhelper.get_listing(bec.credential.user.name, bec.homedir_uri)

        try:
            # successful listing
            return render_to_response('yabi/backend_cred_test.html', dict_join(template_vars, {
                'listing': json.loads(rawdata)
            }))

        except ValueError:
            # value error report
            return render_to_response('yabi/backend_cred_test.html', dict_join(template_vars, {
                'error': "Value Error",
                'error_help': "<pre>" + rawdata + "</pre>"
            }))

    except backendhelper.BackendServerError as bse:
        if "authentication failed" in str(bse).lower():
            # auth failed
            cred_url = '%syabi/credential/%d' % (urlresolvers.reverse('admin:index'), bec.credential.id)  # TODO... construct this more 'correctly'
            return render_to_response('yabi/backend_cred_test.html', dict_join(template_vars, {
                'error': "Authentication Failed",
                'error_help': "The authentication of the test has failed. The <a href='%s'>credential used</a> is most likely incorrect. Please ensure the <a href='%s'>credential</a> is correct." % (cred_url, cred_url)
            }))

        elif "remote host key is denied" in str(bse).lower():
            # remote host key denied.

            # work out which hostkey this is...
            keys = HostKey.objects.filter(hostname=bec.backend.hostname)

            if not keys or len(keys) > 1:
                # link to host key page
                link = '%syabi/hostkey/?hostname=%s' % (urlresolvers.reverse('admin:index'), bec.backend.hostname)  # TODO... construct this more 'correctly'
            else:
                # link to changelist page
                link = '%syabi/hostkey/%d' % (urlresolvers.reverse('admin:index'), keys[0].id)

            logger.info("backend_cred_test tried to test BackendCredential %d and received a denied host key exception [hostname: %s]." % (bec.id, bec.backend.hostname))

            return render_to_response('yabi/backend_cred_test.html', dict_join(template_vars, {
                'error': "Remote Host Key Denied",
                'error_help': "The remote host key has been denied. Please <a href='%s'>check the hostkey</a>'s fingerprint and if it is the correct key, mark it as accepted." % link
            }))

        else:
            # overall exception
            return render_to_response('yabi/backend_cred_test.html', dict_join(template_vars, {
                'error': "Backend Server Error",
                'error_help': "<pre>" + str(bse) + "</pre>"
            }))

    # we should not get here
    assert False, "Unreachable codepoint reached. Something wicked happened"


@staff_member_required
def add_tool(request):

    if request.method == 'GET':
        return render_to_response('yabi/add.html',
                                  {'form': AddToolForm(),
                                   'user': request.user,
                                   'title': 'Add Tool',
                                   'root_path': urlresolvers.reverse('admin:index'),
                                   'action_path': urlresolvers.reverse('add_tool_view'),
                                   'breadcrumb': 'Add Tool'
                                   })
    else:

        f = AddToolForm(request.POST)
        if not f.is_valid():
            return render_to_response('yabi/add.html',
                                      {'form': f,
                                       'user': request.user,
                                       'title': 'Add Tool',
                                       'root_path': urlresolvers.reverse('admin:index'),
                                       'action_path': urlresolvers.reverse('add_tool_view'),
                                       'breadcrumb': 'Add Tool'
                                       })

        else:

            tool_dict = json.loads(f.cleaned_data["tool_json"])
            tool_dict = tool_dict["tool"]
            tool = create_tool(request, tool_dict)

            return HttpResponseRedirect(urlresolvers.reverse('admin:yabi_tool_change', args=(tool.id,)))


@staff_member_required
def create_tool(request, tool_dict):
    # try and get the backends
    try:
        backend = Backend.objects.get(name=tool_dict['backend'])
    except ObjectDoesNotExist as e:
        backend = Backend.objects.get(name='nullbackend')

    try:
        fs_backend = Backend.objects.get(name=tool_dict['fs_backend'])
    except ObjectDoesNotExist as e:
        fs_backend = Backend.objects.get(name='nullbackend')

    # create the tool
    tool = Tool(name=tool_dict["name"],
                display_name=tool_dict["display_name"],
                path=tool_dict["path"],
                description=tool_dict["description"],
                enabled=tool_dict["enabled"],
                backend=backend,
                fs_backend=fs_backend,
                accepts_input=tool_dict["accepts_input"],
                cpus=tool_dict["cpus"],
                walltime=tool_dict["walltime"],
                module=tool_dict["module"],
                queue=tool_dict["queue"],
                max_memory=tool_dict["max_memory"],
                job_type=tool_dict["job_type"]
                )
    tool.save()

    # add the output extensions
    for output_ext in tool_dict["outputExtensions"]:
        extension, created = FileExtension.objects.get_or_create(pattern=output_ext["file_extension__pattern"])
        tooloutputextension, created = ToolOutputExtension.objects.get_or_create(
            tool=tool,
            file_extension=extension,
            must_exist=output_ext["must_exist"],
            must_be_larger_than=output_ext["must_be_larger_than"])

    # add the tool parameters
    for parameter in tool_dict["parameter_list"]:

        toolparameter = ToolParameter(tool=tool,
                                      rank=parameter["rank"],
                                      mandatory=parameter["mandatory"],
                                      file_assignment=parameter["file_assignment"],
                                      output_file=parameter["output_file"],
                                      default_value=parameter["default_value"],
                                      helptext=parameter["helptext"],
                                      switch=parameter["switch"],
                                      hidden=parameter["hidden"],
                                      batch_bundle_files=parameter["batch_bundle_files"]
                                      )

        if parameter["switch_use__display_text"] and parameter["switch_use__formatstring"] and parameter["switch_use__description"]:
            switch_use, created = ParameterSwitchUse.objects.get_or_create(display_text=parameter["switch_use__display_text"],
                                                                           formatstring=parameter["switch_use__formatstring"],
                                                                           description=parameter["switch_use__description"])
        else:
            # default to use "both" tool switch
            switch_use, created = ParameterSwitchUse.objects.get_or_create(display_text='both',
                                                                           formatstring=r'%(switch)s %(value)s',
                                                                           description='Both the switch and the value will be passed in the argument list. They will be separated by a space.')

        toolparameter.switch_use = switch_use
        toolparameter.save()  # so we can add many-to-many on accepted_filetypes

        # for each of the accepted filetype extension glob patterns get all associated filetypes and add them to tool parameter
        for ext_glob in parameter["acceptedExtensionList"]:
            fileextensions = FileExtension.objects.filter(pattern=ext_glob)
            for fe in fileextensions:
                filetypes = fe.filetype_set.all()
                for ft in filetypes:
                    toolparameter.accepted_filetypes.add(ft)

        # input extensions
        # TODO need to decide how to handle these, they are not in the tool json

        if parameter["possible_values"]:
            toolparameter.possible_values = json.dumps(parameter["possible_values"])

        toolparameter.save()

    # we need to do this in a separate loop otherwise the param we want to refer to doesn't exist yet
    for parameter in tool_dict["parameter_list"]:

        # add use_output_filename
        if "use_output_filename__switch" in parameter and parameter['use_output_filename__switch']:
            try:
                outputfilename_toolparameter = ToolParameter.objects.get(tool=tool, switch=parameter["use_output_filename__switch"])
                toolparameter = ToolParameter.objects.get(tool=tool, switch=parameter["switch"])
                toolparameter.use_output_filename = outputfilename_toolparameter
                toolparameter.save()
            except ObjectDoesNotExist as e:
                logger.critical("Unable to add use_output_filename on parameter.use_output_filename field: %s" % e)

        # add extension param
        if "extension_param" in parameter:
            try:
                extension = FileExtension.objects.get(pattern=parameter["extension_param"])
                toolparameter = ToolParameter.objects.get(tool=tool, switch=parameter["switch"])
                toolparameter.extension_param = extension
                toolparameter.save()
            except ObjectDoesNotExist as e:
                logger.critical("Unable to add extension on parameter.extension field: %s" % e)

    tool.save()
    return tool

from yabiadmin.crypto_utils import DecryptException


def render_cred_password_form(request):
    ids = request.GET.get('ids', [])
    action = request.GET.get('action', None)

    render_data = {'h': webhelpers,
                   'return_url': webhelpers.url("/ws/manage_credential/"),
                   'ids': ids,
                   'request': request,
                   'LANGUAGE_CODE': "en",
                   'title': "%s Credential" % action.capitalize(),
                   'user': request.user,
                   'root_path': webhelpers.url("/"),
                   'action': action,
                   'plural': 's',
                   }

    return render_to_response('yabi/crypt_password.html', render_data)


@login_required
def duplicate_credential(request):

    if request.method == 'POST':

        # bail early if canceled
        if 'button' in request.POST and request.POST['button'] == "Cancel":
            messages.info(request, "No changes made.")
            return HttpResponseRedirect(webhelpers.url("/admin-pane/yabi/credential/?ids=%s" % (request.POST['ids'])))

        ids = [int(X) for X in request.POST.get('ids', '').split(',')]
        action = request.POST.get('action')

        success, fail = 0, 0

        # duplicate
        if action == 'duplicate':
            for id in ids:
                cred = Credential.objects.get(id=id)

                try:
                    cred.id = None
                    cred.description = "%s (copy)" % cred.description
                    cred.encrypted2protected(request.POST["password"])
                    cred.save()
                    success += 1
                except DecryptException:
                    fail += 1

        # cache
        if action == 'cache':
            for id in ids:
                cred = Credential.objects.get(id=id)
                try:
                    cred.send_to_cache()
                    success += 1
                except DecryptException:
                    # failed decrypt. not saved.
                    fail += 1

        msg = "%s credential%s successful. %s credential%s failed." % (success, "s" if success != 1 else "", fail, "s" if fail != 1 else "")

        # default is all successful
        level = messages.SUCCESS

        # no successes
        if fail and not success:
            level = messages.ERROR

        # some success
        if fail and success:
            level = messages.WARNING

        messages.add_message(request, level, msg)

        return HttpResponseRedirect(webhelpers.url("/admin-pane/yabi/credential/?ids=%s" % (request.POST['ids'])))

    else:
        return render_cred_password_form(request)


@staff_member_required
def test_exception(request):
    raise Exception('Test exception')


@staff_member_required
def status(request):

    def anyfn(fn, iterable):
        for e in iterable:
            if fn(e):
                return True
        return False

    render_data = {
        'request': request,
        'title': 'Admin Status',
        'user': request.user,
        'root_path': webhelpers.url("/"),
        'settings': get_safe_settings(),
    }

    return render_to_response('yabi/admin_status.html', render_data)
