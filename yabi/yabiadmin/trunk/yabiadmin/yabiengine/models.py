# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Q
from django.conf import settings
from yabiadmin.yabmin.models import User
from yabiadmin.yabiengine import backendhelper
from yabiadmin.yabiengine.urihelper import uriparse
from django.utils import simplejson as json, webhelpers
from django.db.models.signals import post_save
from django.utils.webhelpers import url
import httplib, os
from yabiadmin.yabiengine.urihelper import uriparse, url_join
from urllib import urlencode

import logging
logger = logging.getLogger('yabiengine')


class Status(object):
    def get_status_colour(obj, status):
        if settings.STATUS['pending'] == status:
            return 'grey'
        elif settings.STATUS['ready'] == status:
            return 'orange'
        elif settings.STATUS['requested'] == status:
            return 'green'
        elif settings.STATUS['complete'] == status:
            return 'green'
        elif settings.STATUS['error'] == status:
            return 'red'

class Editable(object):
    @models.permalink
    def edit_url(obj):
        admin_str = 'admin:%s_%s_change' % (obj._meta.app_label, obj._meta.object_name.lower())
        return (admin_str, (obj.id,))

    def edit_link(obj):
        return '<a href="%s">Edit</a>' % obj.edit_url()
    edit_link.short_description = 'Edit'
    edit_link.allow_tags = True


class Workflow(models.Model, Editable, Status):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    json = models.TextField(blank=True)
    log_file_path = models.CharField(max_length=1000,null=True)
    last_modified_on = models.DateTimeField(null=True, auto_now=True, editable=False)
    created_on = models.DateTimeField(auto_now_add=True, editable=False)
    status = models.TextField(max_length=64, blank=True)
    yabistore_id = models.IntegerField(null=True)                           # ALTER TABLE yabiengine_workflow ADD COLUMN yabistore_id INTEGER;
    stageout = models.CharField(max_length=1000)

    def __unicode__(self):
        return self.name

    @property
    def workflowid(self):
        return self.id

    @models.permalink
    def summary_url(self):
        return ('workflow_summary', (), {'workflow_id': self.id})

    def summary_link(self):
        return '<a href="%s">Summary</a>' % self.summary_url()

    summary_link.short_description = 'Summary'
    summary_link.allow_tags = True

    # TODO REFACTOR
    # moved this from job to the workflow level, would be nice to put it at the engine workflow
    # level, but I am worried about the impact on the django signals which reference Job and Workflow
    # and not EngineJob or EngineWorkflow
    def update_json(self, job, data={}):
        json_object = json.loads(self.json)
        job_id = int(job.order)
        assert json_object['jobs'][job_id]['jobId'] == job_id + 1 # jobs are 1 indexed in json

        # status
        json_object['jobs'][job_id]['status'] = job.status

        # data
        for key in data:
            json_object['jobs'][job_id][key] = data[key]

        #stageout
        if job.stageout:
            json_object['jobs'][job_id]['stageout'] = job.stageout

        self.json = json.dumps(json_object)
        self.save() # this triggers an update on yabistore


class Job(models.Model, Editable, Status):
    workflow = models.ForeignKey(Workflow)
    order = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    cpus = models.CharField(max_length=64, null=True, blank=True)
    walltime = models.CharField(max_length=64, null=True, blank=True)
    module = models.TextField(null=True, blank=True)
    queue = models.CharField(max_length=50, default='normal', null=True, blank=True)
    max_memory = models.PositiveIntegerField(null=True, blank=True)
    job_type = models.CharField(max_length=40, default='single', null=True, blank=True)
    status = models.CharField(max_length=64, blank=True)
    exec_backend = models.CharField(max_length=256)
    fs_backend = models.CharField(max_length=256)
    command = models.TextField()
    commandparams = models.TextField(blank=True)
    job_stageins = models.TextField(blank=True)
    input_filetype_extensions = models.TextField(blank=True)
    stageout = models.CharField(max_length=1000, null=True)


    def __unicode__(self):
        return "%s - %s" % (self.workflow.name, self.order)

    def status_ready(self):
        return self.status == settings.STATUS['ready']

    def status_complete(self):
        return self.status == settings.STATUS['complete']

    @property
    def workflowid(self):
        return self.workflow.id


class Task(models.Model, Editable, Status):
    job = models.ForeignKey(Job)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    job_identifier = models.TextField(blank=True)
    command = models.TextField(blank=True)
    exec_backend = models.CharField(max_length=256, blank=True)
    fs_backend = models.CharField(max_length=256, blank=True)
    error_msg = models.CharField(max_length=1000, null=True, blank=True)
    status = models.CharField(max_length=64, blank=True)
    working_dir = models.CharField(max_length=256, null=True, blank=True)
    name = models.CharField(max_length=256, null=True, blank=True)                  # if we are null, we behave the old way and use our task.id

    def json(self):
        # formulate our status url and our error url
        if 'YABIADMIN' in os.environ:                                                   # if we are forced to talk to a particular admin
            statusurl = "http://%sengine/status/task/%d"%(os.environ['YABIADMIN'],self.id)
            errorurl = "http://%sengine/error/task/%d"%(os.environ['YABIADMIN'],self.id)
        else:
            # use the yabiadmin embedded in this server
            statusurl = webhelpers.url("/engine/status/task/%d" % self.id)
            errorurl = webhelpers.url("/engine/error/task/%d" % self.id)

        fsscheme, fsbackend_parts = uriparse(self.job.fs_backend)

        output = {
            "yabiusername":self.job.workflow.user.name,
            "taskid":self.id,
            "statusurl":statusurl,
            "errorurl":errorurl,
            "stagein":[],
            "exec":{
                "command":self.command,
                "backend": url_join(self.job.exec_backend),
                "fsbackend": url_join(self.job.fs_backend, self.working_dir),
                "workingdir": os.path.join(fsbackend_parts.path,self.working_dir),
                "cpus": self.job.cpus,
                "walltime": self.job.walltime,
                "module": self.job.module,
                "queue": self.job.queue,
                "max_memory":self.job.max_memory,
                "job_type":self.job.job_type
                },
            "stageout":self.job.stageout+"/"+("" if not self.name else self.name+"/")
            }

        stageins = self.stagein_set.all()
        for s in stageins:
            src_backend = backendhelper.get_backendcredential_for_uri(self.job.workflow.user.name,s.src).backend
            src_scheme, src_rest = uriparse(s.src)
            dst_backend = backendhelper.get_backendcredential_for_uri(self.job.workflow.user.name,s.dst).backend
            dst_scheme, dst_rest = uriparse(s.dst)


            output["stagein"].append({"src":s.src, "dst":s.dst, "order":s.order})

        return json.dumps(output)

    def __unicode__(self):
        return self.job_identifier

    @property
    def workflowid(self):
        return self.job.workflow.id

    def link_to_syslog(self):
        return '<a href="%s?table_name=task&table_id=%d">%s</a>' % (url('/admin/yabiengine/syslog/'), self.id, "Syslog")
    link_to_syslog.allow_tags = True
    link_to_syslog.short_description = "Syslog"



class StageIn(models.Model, Editable):
    src = models.CharField(max_length=256)
    dst = models.CharField(max_length=256)
    order = models.IntegerField()
    task = models.ForeignKey(Task)

    @property
    def workflowid(self):
        return self.task.job.workflow.id


class QueueBase(models.Model):
    class Meta:
        abstract = True

    workflow = models.ForeignKey(Workflow) 
    created_on = models.DateTimeField(auto_now_add=True)

    def name(self):
        return self.workflow.name

    def user_name(self):
        return self.workflow.user.name

class QueuedWorkflow(QueueBase):
    pass

class Syslog(models.Model):
    message = models.TextField(blank=True)
    table_name = models.CharField(max_length=64, null=True)
    table_id = models.IntegerField(null=True)
    created_on = models.DateTimeField(null=True, auto_now=True, editable=False)

    def __unicode__(self):
        return self.message

    def json(self):
        return json.dumps({ 'table_name':self.table_name,
                            'table_id':self.table_id,
                            'message':self.message
                            }
                          )


# must import this here to avoid circular reference
from yabiengine import wfwrangler

