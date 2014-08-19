#!/usr/bin/env python
from datetime import datetime
import six
from collections import OrderedDict
from itertools import takewhile
import logging


class Settings:
    user = None
    orm = None


settings = Settings()


def set_default_user(user):
    settings.user = user


def set_default_orm(orm):
    settings.orm = orm


def auth_user(username, password, email, active=True, staff=False, superuser=False, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    authuser = orm['auth.user']()
    authuser.last_modified_by = user or authuser
    authuser.last_modified_on = datetime.now()
    authuser.created_by = user or authuser
    authuser.created_on = datetime.now()
    authuser.username = six.text_type(username)
    authuser.password = make_password_hash(password)
    authuser.email = email
    authuser.is_active = active
    authuser.is_staff = staff
    authuser.is_superuser = superuser
    return authuser


def make_password_hash(password):
    import random
    import hashlib
    from django.contrib.auth.hashers import make_password
    salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
    return make_password(password, salt=salt, hasher='sha1')


def yabi_user(username, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_user = orm['yabi.User']()
    yabi_user.last_modified_by = user
    yabi_user.last_modified_on = datetime.now()
    yabi_user.created_by = user
    yabi_user.created_on = datetime.now()
    yabi_user.name = username

    return yabi_user


def yabi_backend(name, description, scheme, hostname, port, path, max_connections=None, lcopy=True, link=True, submission='', user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_backend = orm['yabi.Backend']()
    yabi_backend.last_modified_by = user
    yabi_backend.last_modified_on = datetime.now()
    yabi_backend.created_by = user
    yabi_backend.created_on = datetime.now()
    yabi_backend.name = name
    yabi_backend.description = description
    yabi_backend.scheme = scheme
    yabi_backend.hostname = hostname
    yabi_backend.port = port
    yabi_backend.path = path
    yabi_backend.max_connections = max_connections
    yabi_backend.lcopy_supported = lcopy
    yabi_backend.link_supported = link
    yabi_backend.submission = submission
    return yabi_backend


def yabi_credential(credentialuser, description, username="", password="", cert="", key="", user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_credential = orm['yabi.Credential']()
    yabi_credential.last_modified_by = user
    yabi_credential.last_modified_on = datetime.now()
    yabi_credential.created_by = user
    yabi_credential.created_on = datetime.now()
    yabi_credential.description = description
    yabi_credential.username = username
    yabi_credential.password = password
    yabi_credential.cert = cert
    yabi_credential.key = key
    yabi_credential.user = credentialuser
    yabi_credential.expires_on = datetime(2111, 1, 1, 12, 0)

    yabi_credential.encrypted = False
    yabi_credential.encrypt_on_login = False

    return yabi_credential


def yabi_backendcredential(backend, credential, homedir, visible=False,
                           default_stageout=False, submission='', user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_backendcredential = orm['yabi.BackendCredential']()
    yabi_backendcredential.last_modified_by = user
    yabi_backendcredential.last_modified_on = datetime.now()
    yabi_backendcredential.created_by = user
    yabi_backendcredential.created_on = datetime.now()
    yabi_backendcredential.backend = backend
    yabi_backendcredential.credential = credential
    yabi_backendcredential.homedir = homedir
    yabi_backendcredential.visible = visible
    yabi_backendcredential.default_stageout = default_stageout
    yabi_backendcredential.submission = submission
    return yabi_backendcredential


def yabi_filetype(name, description, extension_list, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_filetype = orm['yabi.FileType']()
    yabi_filetype.last_modified_by = user
    yabi_filetype.last_modified_on = datetime.now()
    yabi_filetype.created_by = user
    yabi_filetype.created_on = datetime.now()
    yabi_filetype.name = name
    yabi_filetype.description = description

    if extension_list:
        yabi_filetype.save()                # gives it an id

    for extension in extension_list:
        yabi_filetype.extensions.add(extension)

    return yabi_filetype


def yabi_parameterswitchuse(display_text, formatstring, description, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_parameterswitchuse = orm['yabi.ParameterSwitchUse']()
    yabi_parameterswitchuse.last_modified_by = user
    yabi_parameterswitchuse.last_modified_on = datetime.now()
    yabi_parameterswitchuse.created_by = user
    yabi_parameterswitchuse.created_on = datetime.now()
    yabi_parameterswitchuse.display_text = display_text
    yabi_parameterswitchuse.formatstring = formatstring
    yabi_parameterswitchuse.description = description
    return yabi_parameterswitchuse


def yabi_tool(name, display_name, path, description, backend, fs_backend,
              enabled=True, accepts_input=False, cpus='', walltime='', module='',
              queue='', max_memory='', job_type='', lcopy=False, link=False,
              user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_tool = orm['yabi.Tool']()
    yabi_tool.last_modified_by = user
    yabi_tool.last_modified_on = datetime.now()
    yabi_tool.created_by = user
    yabi_tool.created_on = datetime.now()
    yabi_tool.name = name
    yabi_tool.display_name = display_name
    yabi_tool.path = path
    yabi_tool.description = description
    yabi_tool.enabled = enabled
    yabi_tool.backend = backend
    yabi_tool.fs_backend = fs_backend
    yabi_tool.accepts_input = accepts_input
    yabi_tool.cpus = cpus
    yabi_tool.walltime = walltime
    yabi_tool.module = module
    yabi_tool.queue = queue
    yabi_tool.max_memory = max_memory
    yabi_tool.job_type = job_type
    yabi_tool.lcopy_supported = lcopy
    yabi_tool.link_supported = link
    return yabi_tool


def yabi_toolparameter(tool, switch, switch_use, rank, mandatory, hidden, output_file, extension_param, possible_values, default_value, helptext, batch_bundle_files, file_assignment, use_output_filename, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_toolparameter = orm['yabi.ToolParameter']()
    yabi_toolparameter.last_modified_by = user
    yabi_toolparameter.last_modified_on = datetime.now()
    yabi_toolparameter.created_by = user
    yabi_toolparameter.created_on = datetime.now()
    yabi_toolparameter.tool = tool
    yabi_toolparameter.switch = switch
    yabi_toolparameter.switch_use = switch_use
    yabi_toolparameter.rank = rank
    yabi_toolparameter.mandatory = mandatory
    yabi_toolparameter.hidden = hidden
    yabi_toolparameter.output_file = output_file
    yabi_toolparameter.extension_param = extension_param
    yabi_toolparameter.possible_values = possible_values
    yabi_toolparameter.default_value = default_value
    yabi_toolparameter.helptext = helptext
    yabi_toolparameter.batch_bundle_files = batch_bundle_files
    yabi_toolparameter.file_assignment = file_assignment
    yabi_toolparameter.use_output_filename = use_output_filename
    return yabi_toolparameter


def yabi_tooloutputextension(tool, extension, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_tooloutputextension = orm['yabi.ToolOutputExtension']()
    yabi_tooloutputextension.last_modified_by = user
    yabi_tooloutputextension.last_modified_on = datetime.now()
    yabi_tooloutputextension.created_by = user
    yabi_tooloutputextension.created_on = datetime.now()
    yabi_tooloutputextension.tool = tool
    yabi_tooloutputextension.file_extension = extension

    yabi_tooloutputextension.must_exist = None
    yabi_tooloutputextension.must_be_larger_than = None

    return yabi_tooloutputextension


def yabi_toolgroup(name, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_toolgroup = orm['yabi.ToolGroup']()
    yabi_toolgroup.last_modified_on = datetime.now()
    yabi_toolgroup.last_modified_by = user
    yabi_toolgroup.created_on = datetime.now()
    yabi_toolgroup.created_by = user
    yabi_toolgroup.name = name
    return yabi_toolgroup


def yabi_toolset(name, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_toolset = orm['yabi.ToolSet']()
    yabi_toolset.last_modified_on = datetime.now()
    yabi_toolset.last_modified_by = user
    yabi_toolset.created_on = datetime.now()
    yabi_toolset.created_by = user
    yabi_toolset.name = name
    return yabi_toolset


def yabi_toolgrouping(toolgroup, tool, toolset, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    yabi_toolgrouping = orm['yabi.ToolGrouping']()
    yabi_toolgrouping.last_modified_on = datetime.now()
    yabi_toolgrouping.last_modified_by = user
    yabi_toolgrouping.created_on = datetime.now()
    yabi_toolgrouping.created_by = user
    yabi_toolgrouping.tool_group = toolgroup
    yabi_toolgrouping.tool = tool
    yabi_toolgrouping.tool_set = toolset
    return yabi_toolgrouping


def yabi_fileextension(pattern, user=None, orm=None):
    user = user or settings.user
    orm = orm or settings.orm

    fileextension = orm['yabi.FileExtension']()
    fileextension.last_modified_by = user
    fileextension.last_modified_on = datetime.now()
    fileextension.created_by = user
    fileextension.created_on = datetime.now()
    fileextension.pattern = pattern
    return fileextension


logger = logging.getLogger("migration")


def deduplicate_tool_descs(Tool, ToolDesc, dry_run=False):
    def tool_key(tool):
        # Important fields for the tool desc are path and accepts_input.
        # name is a unique field, and display name will change
        # depending on backend.
        # Parameters and extensions are important, but the tool
        # groupings aren't.
        return (tool.path, tool.accepts_input,
                tuple(map(param_key, tool.toolparameter_set.order_by("id"))),
                tuple(map(ext_key, tool.tooloutputextension_set.order_by("id"))))

    def param_key(param):
        return (param.switch, param.switch_use.display_text,
                param.rank, param.fe_rank,
                param.mandatory, param.common, param.sensitive_data,
                param.hidden, param.output_file,
                param.possible_values or u"",  # nullable text field
                param.default_value or u"",    # ... annoying
                param.batch_bundle_files,
                param.file_assignment)

    def ext_key(ext):
        # only one field of ToolOutputExtension is actually used
        return ext.file_extension.pattern

    # a mapping of tool "key" to ToolDesc.id
    tooldescs = OrderedDict()
    # a mapping of duplicate ToolDesc ids to first ToolDesc.id
    remap = OrderedDict()

    logger.info("Looking through %d ToolDescs..." % ToolDesc.objects.count())

    for desc in ToolDesc.objects.order_by("created_on"):
        key = tool_key(desc)
        if key in tooldescs:
            remap[desc.id] = tooldescs[key]
        else:
            tooldescs[key] = desc.id

    logger.info("%d ToolDescs will be removed" % len(remap))

    # update tools to point to first ToolDesc
    for tool in Tool.objects.filter(desc_id__in=remap.keys()):
        logger.info("Setting Tool %d \"%s\" desc from %d to %d" % (tool.id, tool.desc.name,
                                                                   tool.desc_id,
                                                                   remap[tool.desc_id]))
        tool.desc_id = remap[tool.desc_id]
        if not dry_run:
            tool.save()

    # clean up the duplicates, will cascade delete parameters, etc
    dead = ToolDesc.objects.filter(id__in=remap.keys())
    if dead.exists():
        logger.info("Deleting duplicate ToolDescs (and their related objects)")
        logger.info(", ".join("%s id=%d" % (tool.name, tool.id) for tool in dead))
    else:
        logger.info("No duplicate ToolDescs")

    if not dry_run:
        dead.delete()
