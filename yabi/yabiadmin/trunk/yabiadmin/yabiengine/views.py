# -*- coding: utf-8 -*-
from conf import config

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.shortcuts import render_to_response, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.utils import webhelpers
from django.db import transaction 
from django.utils import simplejson as json
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings

from yabiadmin.yabiengine.models import Task, Job, Workflow, Syslog
from yabiadmin.yabiengine.enginemodels import EngineTask, EngineJob, EngineWorkflow

import logging
logger = logging.getLogger('yabiengine')

def task(request):
    if "origin" not in request.REQUEST:
        return HttpResponseServerError("Error requesting task. No origin identifier set.")
    
    # verify that the requesters origin is correct
    origin = request.REQUEST["origin"]
    ip,port = origin.split(":")
    exp_ip, exp_port = config.config['backend']['port'][0],str(config.config['backend']['port'][1])
    if ip != exp_ip or port != exp_port:
        ipaddress = request.META[ "HTTP_X_FORWARDED_FOR" if "HTTP_X_FORWARDED_FOR" in request.META else "REMOTE_ADDR" ]
        logger.critical("IP %s requested task but had incorrect identifier set. Expected id %s:%s but got %s:%s instead."%(ipaddress,exp_ip,exp_port,ip,port))
        return HttpResponseServerError("Error requesting task. Origin incorrect. This is not the admin you are looking for")
       
    try:
        # only expose tasks that are ready and are intended for the expeceted backend
        tasks = Task.objects.filter(status=settings.STATUS["ready"], expected_ip=exp_ip, expected_port=exp_port)

        if tasks:
            task = tasks[0]
            task.status=settings.STATUS["requested"]
            task.save()
            logger.debug('requested task id: %s command: %s' % (task.id, task.command))
            return HttpResponse(task.json())
        else:
            raise ObjectDoesNotExist("No more tasks")  
        
    except ObjectDoesNotExist:
        return HttpResponseNotFound("Object not found.")
    except Exception, e:
        logger.critical("Caught Exception:")
        import traceback
        logger.critical(e)
        logger.critical(traceback.format_exc())
        return HttpResponseServerError("Error requesting task.")

def status(request, model, id):
    logger.debug('model: %s id: %s' % (model, id))
    models = {'task':EngineTask, 'job':EngineJob, 'workflow':EngineWorkflow}

    # sanity checks
    if model.lower() not in models.keys():
        raise ObjectDoesNotExist()

    try:
        if request.method == "GET":
            m = models[model.lower()]
            obj = m.objects.get(id=id)
            return HttpResponse(json.dumps({"status":obj.status}))

        else:
            if "status" not in request.POST:
                return HttpResponseServerError("POST request to error service should contain 'status' parameter\n")

            # TODO FIXME DELETEME
            # Force some requests to fail, so we can test be retries
            import random
            if random.random() > 0.8:
                logger.debug("Forcing exception")
                return HttpResponseServerError("error")

            model = str(model).lower()
            id = int(id)
            status = str(request.POST["status"])

            # truncate status to 64 chars to avoid any sql field length errors
            status = status[:64]
                
            m = models[model]
            obj = m.objects.get(id=id)
            obj.status=status
            obj.save()

            # update the job status when the task status changes
            if (model == 'task'):
                obj.job.update_status()
                obj.job.save()

            # this is the only place in the code that we trigger walk
            obj.walk()

            return HttpResponse("")

    except (ObjectDoesNotExist,ValueError):
        return HttpResponseNotFound("Object not found")
    except Exception, e:
        import traceback
        logger.critical(traceback.format_exc())
        logger.critical("Caught Exception: %s" % e)
        return HttpResponseServerError(e)


def error(request, table, id):
    logger.debug('table: %s id: %s' % (table, id))
    
    try:

        if request.method == "GET":
            entries = Syslog.objects.filter(table_name=table, table_id=id)

            if not entries:
                raise ObjectDoesNotExist()

            output = [{"table_name":x.table_name, "table_id":x.table_id, "message":x.message} for x in entries]
            return HttpResponse(json.dumps(output))

        else:

            # check we have required params
            if "message" not in request.POST:
                return HttpResponseServerError("POST request to error service should contain 'message' parameter\n")

            syslog = Syslog(table_name=str(table),
                            table_id=int(id),
                            message=str(request.POST["message"])
                            )

            syslog.save()

            return HttpResponse("Thanks!")

    except (ObjectDoesNotExist,ValueError):
        return HttpResponseNotFound("Object not found")
    except Exception, e:
        logger.critical("Caught Exception: %s" % e.message)
        return HttpResponseNotFound("Object not found")


@staff_member_required
def workflow_summary(request, workflow_id):
    logger.debug('')

    workflow = get_object_or_404(Workflow, pk=workflow_id)
        
    return render_to_response('yabiengine/workflow_summary.html', {
                'w': workflow,
                'user':request.user,
                'title': 'Workflow Summary',
                'root_path':webhelpers.url("/admin"),
                'settings':settings
                })
