import logging
import os
from yabiadmin.backend.execbackend import ExecBackend
from yabiadmin.backend.sshexec import SSHExec
from yabiadmin.backend.exceptions import RetryException
from yabiadmin.yabiengine.urihelper import uriparse
import django
logger = logging.getLogger(__name__)


class SchedulerExecBackend(ExecBackend):
    """
    A _abstract_ backend which allows job submission via qsub
    """
    SCHEDULER_NAME = ""

    QSUB_TEMPLATE = "\n".join(["#!/bin/sh",
                    'script_temp_file_name="{0}"',
                    "cat<<EOS>$script_temp_file_name",
                    "{1}",
                    "EOS",
                    "<QSUB_COMMAND> -N {4} -o '{2}' -e '{3}' $script_temp_file_name"])

    QSTAT_TEMPLATE = "\n".join(["#!/bin/sh",
                                "<QSTAT_COMMAND> -f -1 {0}"])


    def __init__(self, *args, **kwargs):
        super(SchedulerExecBackend, self).__init__(*args, **kwargs)
        self.executer = SSHExec()
        self.parser = None
        self.submission_script_name = None
        self.submission_script_body = None
        self.qsub_script_body = None
        self.stdout_file = None
        self.stderr_file = None
        self._task = None
        self._cred = None

    @property
    def task(self):
        return self._task

    @task.setter
    def task(self, val):
        self._task = val
        self.executer.uri = self._task.job.exec_backend

    @property
    def cred(self):
        return self._cred

    @cred.setter
    def cred(self, val):
        self._cred = val
        self.executer.credential = self._cred.credential


    def get_scheduler_command_path(self, scheduler_command):
        from django.conf import settings
        if hasattr(settings, "SCHEDULER_COMMAND_PATHS"):
            if settings.SCHEDULER_COMMAND_PATHS.has_key(self.SCHEDULER_NAME):
                return settings.SCHEDULER_COMMAND_PATHS[self.SCHEDULER_NAME].get(scheduler_command, scheduler_command)
        return scheduler_command


    def _yabi_task_name(self):
        # NB. No hyphens - these got rejected by PBS Pro initially
        # NB. 15 character limit also.
        return "Y{0}".format(self.task.pk)[:15]

    def submit_task(self):
        qsub_result = self._run_qsub()
        if qsub_result.status == qsub_result.JOB_SUBMITTED:
            self._job_submitted_response(qsub_result)
        else:
            self._job_not_submitted_response(qsub_result)


    def _job_submitted_response(self, qsub_result):
        self.task.remote_id = qsub_result.remote_id
        self.task.save()
        logger.info("Yabi Task {0} submitted to {1} OK. remote id = {2}".format(self._yabi_task_name(),
                                                                                     self.SCHEDULER_NAME,
                                                                                     self.task.remote_id))

    def _job_not_submitted_response(self, qsub_result):
        raise Exception("Error submitting remote job to {0} for yabi task {1} {2}".format(self.SCHEDULER_NAME,
                                                                                          self._yabi_task_name(),
                                                                                          qsub_result.status))

    def _run_qsub(self):
        exec_scheme, exec_parts = uriparse(self.task.job.exec_backend)
        working_scheme, working_parts = uriparse(self.working_output_dir_uri())
        self.submission_script_name = self.executer.generate_remote_script_name()
        self.task.job_identifier = self.submission_script_name
        self.task.save()
        logger.debug("creating qsub script %s" % self.submission_script_name)
        self.submission_script_body = self.get_submission_script(exec_parts.hostname, working_parts.path)
        self.stdout_file = os.path.join(working_parts.path, "STDOUT.txt")
        self.stderr_file = os.path.join(working_parts.path, "STDERR.txt")
        self.qsub_script_body = self._get_qsub_body()
        logger.debug("qsub script:\n%s" % self.qsub_script_body)
        stdout, stderr = self.executer.exec_script(self.qsub_script_body)
        logger.debug("_run_qsub:\nSTDOUT:\n%s\nSTDERR:\n%s", stdout, stderr)
        qsub_result = self.parser.parse_qsub(stdout, stderr)
        if qsub_result.status != qsub_result.JOB_SUBMITTED:
            logger.error("Yabi Task Name = %s" % self._yabi_task_name())
            logger.error("Submission script name = %s" % self.submission_script_name)
            logger.error("Submission script body = %s" % self.submission_script_body)
            logger.error("stderr:")
            for line in stderr:
                logger.error(line)
        return qsub_result

    def _get_qsub_body(self):
        return self.QSUB_TEMPLATE.format(
            self.submission_script_name, self.submission_script_body,
            self.stdout_file, self.stderr_file, self._yabi_task_name()).replace("<QSUB_COMMAND>",self.get_scheduler_command_path("qsub"))

    def _get_polling_script(self):
        return self.QSTAT_TEMPLATE.format(self.task.remote_id).replace("<QSTAT_COMMAND>", self.get_scheduler_command_path("qstat"))

    def _run_qstat(self):
        qstat_command = self._get_polling_script()
        stdout, stderr = self.executer.exec_script(qstat_command)
        qstat_result = self.parser.parse_qstat(self.task.remote_id, stdout, stderr)
        return qstat_result

    def _job_running_response(self, qstat_result):
        logger.debug("remote job %s for yabi task %s is stilling running" % (self.task.remote_id, self._yabi_task_name()))
        retry_ex = RetryException("Yabi task %s remote job %s still running" % (self._yabi_task_name(), self.task.remote_id))
        retry_ex.backoff_strategy = RetryException.BACKOFF_STRATEGY_CONSTANT
        retry_ex.type = RetryException.TYPE_POLLING
        raise retry_ex

    def _job_not_found_response(self, qstat_result):
        # NB. for psbpro and torque this is an error, for other subclasses it isn't
        raise NotImplementedError()

    def _job_completed_response(self, qstat_result):
        logger.debug("yabi task %s remote id %s completed" % (self._yabi_task_name(), self.task.remote_id))

    def _unknown_job_status_response(self, qstat_result):
        raise Exception("Yabi task %s unknown state: %s" % (self._yabi_task_name(), qstat_result.status))

    def poll_task_status(self):
        qstat_result = self._run_qstat()
        if qstat_result.status == qstat_result.JOB_RUNNING:
            self._job_running_response(qstat_result)
        elif qstat_result.status == qstat_result.JOB_NOT_FOUND:
            logger.info("qstat for remote job %s of yabi task %s did not produce results" % (self.task.remote_id,
                                                                                             self._yabi_task_name()))
            self._job_not_found_response(qstat_result)
        elif qstat_result.status == qstat_result.JOB_COMPLETED:
            self._job_completed_response(qstat_result)
        else:
            self._unknown_job_status_response(qstat_result)
