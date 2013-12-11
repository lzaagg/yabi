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
from functools import wraps
from django.db import transaction
from datetime import datetime
from yabiadmin.backend.exceptions import RetryException, JobNotFoundException
from yabiadmin.backend import backend
from yabiadmin.constants import STATUS_ERROR, STATUS_READY, STATUS_COMPLETE, STATUS_EXEC, STATUS_STAGEOUT, STATUS_STAGEIN, STATUS_CLEANING, STATUS_ABORTED
from yabiadmin.constants import MAX_CELERY_TASK_RETRIES
from yabiadmin.yabi.models import DecryptedCredentialNotAvailable
from yabiadmin.yabiengine.models import Task
from yabiadmin.yabiengine.enginemodels import EngineWorkflow, EngineJob, EngineTask
import celery
from celery import current_task, chain
from celery.utils.log import get_task_logger
from six.moves import filter
logger = get_task_logger(__name__)


# Celery Tasks working on a Workflow

def process_workflow(workflow_id):
    return chain(create_jobs.s(workflow_id) | process_jobs.s())


@celery.task
def create_jobs(workflow_id):
    workflow = EngineWorkflow.objects.get(pk=workflow_id)
    workflow.create_jobs()
    return workflow.pk


@celery.task
def process_jobs(workflow_id):
    workflow = EngineWorkflow.objects.get(pk=workflow_id)
    if workflow.is_aborting:
        workflow.status = STATUS_ABORTED
        workflow.save()
        return

    for job in workflow.jobs_that_need_processing():
        chain(create_db_tasks.s(job.pk), spawn_ready_tasks.s()).apply_async()


@celery.task
def abort_workflow(workflow_id):
    logger.debug("Aborting workflow %s", workflow_id)
    workflow = EngineWorkflow.objects.get(pk=workflow_id)
    if workflow.status == STATUS_ABORTED:
        return
    not_aborted_tasks = EngineTask.objects.filter(job__workflow__id=workflow.pk).exclude(job__status=STATUS_ABORTED)

    running_tasks = filter(lambda x: x.status == STATUS_EXEC, not_aborted_tasks)
    logger.debug("Found %s running tasks", len(running_tasks))
    for task in running_tasks:
        abort_task.apply_async((task.pk,))


# Celery Tasks working on a Job


@celery.task(max_retries=None)
def create_db_tasks(job_id):
    request = current_task.request
    try:
        job = EngineJob.objects.get(pk=job_id)
        if job.status == STATUS_READY:
            # Handling case when in a previous execution the Celery worker died
            # after tasks have been created and the transaction has been
            # commited, but the Celery task didn't return yet
            assert job.total_tasks() > 0, "Job in READY state, but has no tasks"
            logger.warning("Job was already in READY state. Skipping creation of db tasks.")
            return job_id

        if job.is_workflow_aborting:
            job.status = STATUS_ABORTED
            job.save()
            job.workflow.update_status()
            return None

        tasks_count = job.create_tasks()
        if not tasks_count:
            return None
        return job_id

    except DecryptedCredentialNotAvailable as dcna:
        logger.exception("Decrypted credential not available.")
        countdown = backoff(request.retries)
        logger.warning('create_db_tasks.retry {0} in {1} seconds'.format(job_id, countdown))
        raise current_task.retry(exc=dcna, countdown=countdown)
    except Exception:
        logger.exception("Exception in create_db_tasks for job {0}".format(job_id))
        job.status = STATUS_ERROR
        job.workflow.status = STATUS_ERROR
        job.save()
        job.workflow.save()
        raise


@celery.task()
def spawn_ready_tasks(job_id):
    logger.debug('spawn_ready_tasks for job {0}'.format(job_id))
    if job_id is None:
        logger.debug('no tasks to process, exiting early')
        return
    try:
        # TODO deprecate tasktag
        job = EngineJob.objects.get(pk=job_id)
        ready_tasks = job.ready_tasks()
        logger.debug(ready_tasks)
        aborting = job.is_workflow_aborting

        for task in ready_tasks:
            if aborting:
                task.set_status(STATUS_ABORTED)
                task.save()
            else:
                spawn_task(task.pk)
                # need to update task.job.status here when all tasks for job spawned ?

        if aborting:
            job.status = STATUS_ABORTED
            job.save()
            job.workflow.update_status()

        return job_id

    except Exception:
        logger.exception("Exception when submitting tasks for job {0}".format(job_id))
        job = EngineJob.objects.get(pk=job_id)
        job.status = STATUS_ERROR
        job.workflow.status = STATUS_ERROR
        job.save()
        job.workflow.save()
        raise


# Celery Tasks working on a Yabi Task

def mark_workflow_as_error(task_id):
    logger.debug("Task chain for Task {0} failed.".format(task_id))
    task = Task.objects.get(pk=task_id)
    task.job.status = STATUS_ERROR
    task.job.workflow.status = STATUS_ERROR
    task.job.save()
    task.job.workflow.save()
    logger.debug("Marked Workflow {0} as errored.".format(task.job.workflow.pk))


@transaction.commit_on_success()
def spawn_task(task_id):
    logger.debug('Spawn task {0}'.format(task_id))

    task = Task.objects.get(pk=task_id)
    if task.is_workflow_aborting:
        change_task_status(task_id, STATUS_ABORTED)
        return
    task.set_status('requested')
    task.save()
    transaction.commit()
    task_chain = chain(stage_in_files.s(task_id), submit_task.s(), poll_task_status.s(), stage_out_files.s(), clean_up_task.s())
    task_chain.apply_async()


def retry_on_error(original_function):
    @wraps(original_function)
    def decorated_function(task_id, *args, **kwargs):
        request = current_task.request
        original_function_name = original_function.__name__
        try:
            result = original_function(task_id, *args, **kwargs)
            return result
        except RetryException as rexc:
            if rexc.type == RetryException.TYPE_ERROR:
                logger.exception("Exception in celery task {0} for task {1}".format(original_function_name, task_id))

            if rexc.backoff_strategy == RetryException.BACKOFF_STRATEGY_EXPONENTIAL:
                countdown = backoff(request.retries)
            else:
                # constant for polling
                countdown = 30

            try:
                logger.warning('{0}.retry {1} in {2} seconds'.format(original_function_name, task_id, countdown))
                current_task.retry(exc=rexc, countdown=countdown)
            except RetryException:
                logger.error("{0}.retry {1} exceeded retry limit - changing status to error".format(original_function_name, task_id))
                change_task_status(task_id, STATUS_ERROR)
                raise
            except celery.exceptions.RetryTaskError:
                raise
            except Exception as ex:
                logger.error(("{0}.retry {1} failed: {2} - changing status to error".format(original_function_name, task_id, ex)))
                change_task_status(task_id, STATUS_ERROR)
                mark_workflow_as_error(task_id)
                raise

        except Exception as ex:
            # Retry always
            countdown = backoff(request.retries)
            logger.exception("Unhandled exception in celery task {0}: {1} - retrying anyway ...".format(original_function_name, ex))
            logger.warning('{0}.retry {1} in {2} seconds'.format(original_function_name, task_id, countdown))
            current_task.retry(exc=ex, countdown=countdown)

    return decorated_function


def skip_if_no_task_id(original_function):
    @wraps(original_function)
    def decorated_function(task_id, *args, **kwargs):
        original_function_name = original_function.__name__
        if task_id is None:
            logger.info("%s received no task_id. Skipping processing ", original_function_name)
            return None
        result = original_function(task_id, *args, **kwargs)
        return result

    return decorated_function


@celery.task(max_retries=None)
@retry_on_error
@skip_if_no_task_id
def stage_in_files(task_id):
    task = EngineTask.objects.get(pk=task_id)
    if abort_task_if_needed(task):
        return None
    change_task_status(task.pk, STATUS_STAGEIN)
    backend.stage_in_files(task)
    return task_id


@celery.task(max_retries=MAX_CELERY_TASK_RETRIES)
@retry_on_error
@skip_if_no_task_id
def submit_task(task_id):
    task = EngineTask.objects.get(pk=task_id)
    if abort_task_if_needed(task):
        return None
    change_task_status(task.pk, STATUS_EXEC)
    transaction.commit()
    # Re-fetch task
    task = EngineTask.objects.get(pk=task_id)
    backend.submit_task(task)
    return task_id


@celery.task(max_retries=None)
@retry_on_error
@skip_if_no_task_id
def poll_task_status(task_id):
    task = EngineTask.objects.get(pk=task_id)
    try:
        backend.poll_task_status(task)
        return task_id
    except JobNotFoundException:
        if abort_task_if_needed(task):
            return None
        raise


@celery.task(max_retries=None)
@retry_on_error
@skip_if_no_task_id
def stage_out_files(task_id):
    task = EngineTask.objects.get(pk=task_id)
    if abort_task_if_needed(task):
        return None
    change_task_status(task.pk, STATUS_STAGEOUT)
    backend.stage_out_files(task)
    return task_id


@celery.task(max_retries=None)
@retry_on_error
@skip_if_no_task_id
def clean_up_task(task_id):
    task = EngineTask.objects.get(pk=task_id)
    if abort_task_if_needed(task):
        return None
    change_task_status(task.pk, STATUS_CLEANING)
    backend.clean_up_task(task)
    change_task_status(task.pk, STATUS_COMPLETE)


@celery.task
def abort_task(task_id):
    logger.debug("Aborting task %s", task_id)
    task = EngineTask.objects.get(pk=task_id)
    backend.abort_task(task)


# Implementation

def abort_task_if_needed(task):
    if task.is_workflow_aborting:
        if task.status != STATUS_ABORTED:
            change_task_status(task.pk, STATUS_ABORTED)
        return True
    return False


def backoff(count=0):
    """
    Provide an exponential backoff with a maximum backoff in seconds
    Used to delay between task retries
    """
    if count > 4:
        count = 4
    return 5 ** (count + 1)


# Service methods
# TODO TSZ move to another file?


@transaction.commit_manually()
def change_task_status(task_id, status):
    try:
        logger.debug("Setting status of task {0} to {1}".format(task_id, status))
        task = EngineTask.objects.get(pk=task_id)
        task.set_status(status)
        task.save()
        transaction.commit()

        job_old_status = task.job.status
        job_status = task.job.update_status()
        job_status_changed = (job_old_status != job_status)

        if job_status_changed:
            transaction.commit()
            task.job.workflow.update_status()
            # commit before submission of Celery Tasks
            transaction.commit()
            process_workflow_jobs_if_needed(task)

        transaction.commit()

    except Exception:
        transaction.rollback()
        logger.exception("Exception when updating task's {0} status to {1}".format(task_id, status))
        raise


def process_workflow_jobs_if_needed(task):
    workflow = EngineWorkflow.objects.get(pk=task.job.workflow.pk)
    if workflow.is_aborting:
        for job in workflow.jobs_that_wait_for_dependencies():
            logger.debug('Aborting job %s', job.pk)
            job.status = STATUS_ABORTED
            job.save()
        workflow.update_status()
        return
    if task.job.status == STATUS_COMPLETE:
        if workflow.has_jobs_to_process():
            process_jobs.apply_async((workflow.pk,))


@transaction.commit_manually()
def request_workflow_abort(workflow_id, yabiuser=None):
    workflow = EngineWorkflow.objects.get(pk=workflow_id)
    if (workflow.abort_requested_on is not None) or workflow.status in (STATUS_COMPLETE, STATUS_ERROR):
        transaction.commit()
        return False
    workflow.abort_requested_on = datetime.now()
    workflow.abort_requested_by = yabiuser
    workflow.save()
    transaction.commit()
    abort_workflow.apply_async((workflow_id,))
    return True
