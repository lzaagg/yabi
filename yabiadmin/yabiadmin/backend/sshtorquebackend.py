from yabiadmin.backend.qbaseexecbackend import QBaseExecBackend
from yabiadmin.backend.torqueparsers import TorqueParser
from yabiadmin.backend.exceptions import JobNotFoundException


class SSHTorqueExecBackend(QBaseExecBackend):
    SCHEDULER_NAME = "torque"
    QSTAT_TEMPLATE = "\n".join(["#!/bin/sh",
                                "<QSTAT_COMMAND> -f -1 {0}"])

    backend_scheme = "ssh+torque"

    def __init__(self, *args, **kwargs):
        super(SSHTorqueExecBackend, self).__init__(*args, **kwargs)
        self.parser = TorqueParser()

    def _job_not_found_response(self, qstat_result):
        raise JobNotFoundException("Remote job %s for Yabi task %s not found by qstat" % (self.task.remote_id, self._yabi_task_name()))
