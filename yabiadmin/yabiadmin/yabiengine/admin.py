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
# -*- coding: utf-8 -*-
from yabiadmin.yabi.models import User
from yabiadmin.yabiengine.models import *
from yabiadmin.yabiengine.enginemodels import *

from django.contrib import admin
from django.contrib import messages
from yabiadmin.yabiengine import storehelper as StoreHelper
from yabiadmin.backend.celerytasks import request_workflow_abort


def link_to_jobs(obj):
    return '<a href="%s?workflow__exact=%d">%s</a>' % (url('/admin-pane/yabiengine/job/'), obj.workflowid, "Jobs")
link_to_jobs.allow_tags = True
link_to_jobs.short_description = "Jobs"


def link_to_tasks(obj):
    return '<a href="%s?job__workflow__exact=%d">%s</a>' % (url('/admin-pane/yabiengine/task/'), obj.workflowid, "Tasks")
link_to_tasks.allow_tags = True
link_to_tasks.short_description = "Tasks"


def link_to_tasks_from_job(obj):
    return '<a href="%s?job__workflow__exact=%d&job__exact=%d">%s</a>' % (url('/admin-pane/yabiengine/task/'), obj.workflowid, obj.id, "Tasks")
link_to_tasks_from_job.allow_tags = True
link_to_tasks_from_job.short_description = "Tasks"


def link_to_stageins(obj):
    return '<a href="%s?task__job__workflow__exact=%d">%s</a>' % (url('/admin-pane/yabiengine/stagein/'), obj.workflowid, "Stageins")
link_to_stageins.allow_tags = True
link_to_stageins.short_description = "Stageins"


def link_to_stageins_from_task(obj):
    return '<a href="%s?task__job__workflow__exact=%d&task__exact=%d">%s</a>' % (url('/admin-pane/yabiengine/stagein/'), obj.workflowid, obj.id, "Stageins")
link_to_stageins_from_task.allow_tags = True
link_to_stageins_from_task.short_description = "Stageins"


def link_to_syslog_from_task(obj):
    return '<a href="%s?table_name=task&table_id=%d">%s</a>' % (url('/admin-pane/yabiengine/syslog/'), obj.id, "Syslog")
link_to_syslog_from_task.allow_tags = True
link_to_syslog_from_task.short_description = "Syslog"


class BaseModelAdmin(admin.ModelAdmin):
    """
    Allows for whitelisting filters to be passed in via query string
    See: http://www.hoboes.com/Mimsy/hacks/fixing-django-124s-suspiciousoperation-filtering/
    """
    valid_lookups = ()

    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup.startswith(self.valid_lookups):
            return True
        return super(BaseModelAdmin, self).lookup_allowed(lookup, *args, **kwargs)


class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'stageout', link_to_jobs, link_to_tasks, link_to_stageins, 'summary_link', 'is_aborting']
    list_filter = ['status', 'user']
    search_fields = ['name']
    actions = ['archive_workflow', 'abort_workflow']
    fieldsets = (
        (None, {
            'fields': ('name', 'user', 'start_time', 'end_time', 'status', 'stageout')
        }),
    )

    def archive_workflow(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)

        for id in selected:
            wf = EngineWorkflow.objects.get(id=id)
            success = StoreHelper.archiveWorkflow(wf)

        if success:
            if len(selected):
                if len(selected) == 1:
                    message_bit = "1 workflow archived."
                else:
                    message_bit = "%s workflows were archived." % len(selected)

                messages.success(request, message_bit)
        else:
            messages.error(request, "Couldn't archive workflow(s)!")

        # pass on to delete action
        #return delete_selected(self, request, queryset)

    archive_workflow.short_description = "Archive selected Workflows."

    def abort_workflow(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)

        counter = 0
        for id in selected:
            yabiuser = User.objects.get(name=request.user.username)
            if request_workflow_abort(id, yabiuser):
                counter += 1

        if counter == 1:
            message_bit = "1 workflow was requested to abort."
        else:
            message_bit = "%s workflows were requested to abort." % counter
        messages.success(request, message_bit)

    abort_workflow.short_description = "Abort selected Workflows."


class QueuedWorkflowAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'created_on']


class SyslogAdmin(admin.ModelAdmin):
    list_display = ['message', 'table_name', 'table_id', 'created_on']
    search_fields = ['table_name', 'table_id']


class JobAdmin(admin.ModelAdmin):

    def workflow_name(obj):
        return obj.workflow.name

    list_display = [workflow_name, 'order', 'status', 'command', 'start_time', 'end_time', 'cpus', 'walltime', link_to_tasks_from_job]
    ordering = ['order']
    fieldsets = (
        (None, {
            'fields': ('workflow', 'order', 'start_time', 'cpus', 'walltime', 'module', 'queue', 'max_memory', 'job_type', 'status', 'exec_backend', 'fs_backend', 'command', 'stageout', 'preferred_stagein_method', 'preferred_stageout_method', 'task_total')
        }),
    )
    raw_id_fields = ['workflow']


class TaskAdmin(BaseModelAdmin):
    valid_lookups = ('job__workflow__exact',)

    def workflow(task):
        workflow = task.job.workflow
        return '<a href="/admin-pane/yabiengine/engineworkflow/%s">%s</a>' % (workflow.pk, workflow.name)
    workflow.allow_tags = True

    list_display = ['id', workflow, 'start_time', 'end_time', 'job_identifier', 'error_msg', 'command', link_to_stageins_from_task, link_to_syslog_from_task]
    list_filter = ['job__workflow__user']
    search_fields = ['id']
    raw_id_fields = ['job']
    fieldsets = (
        (None, {
            'fields': ('job', 'start_time', 'end_time', 'job_identifier', 'command', 'task_num', 'error_msg')
        }),
        ('Remote Information', {
            'classes': ('collapse',),
            'fields': ('remote_id', 'remote_info', 'working_dir', 'name', 'tasktag')
        }),
        ('Status Information', {
            'classes': ('collapse',),
            'fields': ('status_pending', 'status_ready', 'status_requested', 'status_stagein', 'status_mkdir', 'status_exec',
                       'status_exec_unsubmitted', 'status_exec_pending', 'status_exec_active', 'status_exec_running', 'status_exec_cleanup',
                       'status_exec_done', 'status_exec_error', 'status_stageout', 'status_cleaning', 'status_complete', 'status_error', 'status_aborted', 'status_blocked')
        }),
    )


class StageInAdmin(BaseModelAdmin):
    valid_lookups = ('task__job__workflow__exact',)
    list_display = ['src', 'dst', 'order', 'method']
    raw_id_fields = ['task']


def register(site):
    site.register(EngineWorkflow, WorkflowAdmin)
    site.register(QueuedWorkflow, QueuedWorkflowAdmin)
    site.register(Syslog, SyslogAdmin)
    site.register(Job, JobAdmin)
    site.register(Task, TaskAdmin)
    site.register(StageIn, StageInAdmin)
