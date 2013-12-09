# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender                0 Q normal
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender                0 Q normal
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender                0 Q normal
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender                0 Q normal
# [lrender@carah ~]$
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender                0 Q normal
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender                0 Q normal
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender                0 Q normal
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender                0 Q normal
# [lrender@carah ~]$ ls
# test.sh
# [lrender@carah ~]$ pwd
# /export/home/tech/lrender
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender         00:00:00 C normal
# [lrender@carah ~]$ qstat
# Job id                    Name             User            Time Use S Queue
# ------------------------- ---------------- --------------- -------- - -----
# 42903.carah               test.sh          lrender         00:00:00 C normal
#
import re
import logging
import string
from six.moves import map
from six.moves import zip
logger = logging.getLogger(__name__)


class TorqueQSubResult(object):
    JOB_SUBMITTED = "job submitted"
    JOB_SUBMISSION_ERROR = "job submission error"

    def __init__(self):
        self.status = None
        self.remote_id = None

    def __repr__(self):
        return "qsub result: remote id = %s remote job status = %s" % (self.remote_id, self.status)


class TorqueQStatResult(object):
    JOB_RUNNING = "job running"
    JOB_NOT_FOUND = "job not found by qstat"
    JOB_COMPLETED = "job succeeded"

    def __init__(self):
        self.status = None
        self.remote_id = None
        self.remote_status = None  # raw result of qstat

    def __repr__(self):
        return "qstat result: remote id = %s remote job status = %s" % (self.remote_id, self.status)


class TorqueQDelResult(object):
    JOB_ABORTED = "JOB ABORTED"
    JOB_ABORTION_ERROR = "JOB ABORTION ERROR"
    JOB_FINISHED = "JOB FINISHED"

    def __init__(self):
        self.status = None
        self.error = None


class TorqueParser(object):
    JOB_NUMBER_PATTERN = r'^(?P<remote_id>\d+(?:\[\])?)(\.\w+)+'  # E.g.  1224.carah  or 1234.carah.localdomain or 1224[].carah
    QSTAT_JOB_STATE_INDEX = 4
    #     NB. Possible statuses:
    #     C   Job is completed after having run
    #     E   Job is exiting after having run.
    #     H   Job is held.
    #     Q   job is queued, eligible to run or routed.
    #     R   job is running.
    #     T   job is being moved to new location.
    #     W   job is waiting for its execution time (-a option) to be reached.
    #     S   (Unicos only) job is suspended.
    #     see http://www.clusterresources.com/torquedocs21/commands/qstat.shtml
    POSSIBLE_STATES = ["C", "E", "H", "Q", "R", "T", "W", "S"]
    RUNNING_STATES = ["R", "T", "W", "S", "Q", "H"]
    FINISHED_STATES = ["E", "C"]

    def parse_sub(self, exit_code, stdout, stderr):
        """

        @param stdout: list of lines
        @param stderr: list of lines
        @return: TorqueQSubResult
        """
        qsub_result = TorqueQSubResult()
        if exit_code > 0:
            qsub_result.status = TorqueQSubResult.JOB_SUBMISSION_ERROR
            return qsub_result
        for line in stdout:
            logger.debug("Parsing QSUB output line: [%s]" % line)
            try:
                m = re.match(TorqueParser.JOB_NUMBER_PATTERN, line)
                if m:
                    qsub_result.remote_id = m.group("remote_id")
                    qsub_result.status = TorqueQSubResult.JOB_SUBMITTED
                    return qsub_result
            except:
                qsub_result.status = TorqueQSubResult.JOB_SUBMISSION_ERROR
                return qsub_result

        qsub_result.status = TorqueQSubResult.JOB_SUBMISSION_ERROR
        return qsub_result

    def _parse_qstat_line(self, line):
        """
        @param prefix: The string before =  ( e.g. "job_state" )
        @param line: eg "job_state = C"
        @return: the value after = stripped ( E.g. "C" in above case
        """
        # AH added the list after running modernize
        parts = list(map(string.strip, line.split("=")))
        return parts[1]

    def parse_poll(self, remote_id, exit_code, stdout, stderr):
        """
        parsing result of: qstat -f -1 <remote_id>:

        [lrender@carah ~]$ qstat -f -1  42944
                Job Id: 42944.carah.localdomain
                Job_Name = test.sh
                Job_Owner = lrender@carah.localdomain
                resources_used.cput = 00:00:00
                resources_used.mem = 0kb
                resources_used.vmem = 0kb
                resources_used.walltime = 00:00:00
                job_state = C
                queue = normal
                server = carah.localdomain
                Checkpoint = u
                ctime = Mon Aug 12 15:19:13 2013
                Error_Path = carah.localdomain:/export/home/tech/lrender/test.sh.e42944
                exec_host = carah/0
                Hold_Types = n
                Join_Path = n
                Keep_Files = n
                Mail_Points = a
                mtime = Mon Aug 12 15:19:43 2013
                Output_Path = carah.localdomain:/export/home/tech/lrender/test.sh.o42944
                Priority = 0
                qtime = Mon Aug 12 15:19:13 2013
                Rerunable = True
                Resource_List.nodect = 1
                Resource_List.nodes = 1
                Resource_List.walltime = 01:00:00
                session_id = 16857
                Variable_List = PBS_O_HOME=/export/home/tech/lrender,PBS_O_LANG=en_AU.UTF-8,PBS_O_LOGNAME=lrender,PBS_O_PATH=/usr/kerberos/bin:/usr/local/bin:/bin:/usr/bin:/opt/torque/2.3.13/bin/:/export/home/tech/lrender/bin,PBS_O_MAIL=/var/spool/mail/lrender,PBS_O_SHELL=/bin/bash,PBS_O_HOST=carah.localdomain,PBS_SERVER=carah,PBS_O_WORKDIR=/export/home/tech/lrender,PBS_O_QUEUE=normal
                etime = Mon Aug 12 15:19:13 2013
                exit_status = 127
                submit_args = test.sh
                start_time = Mon Aug 12 15:19:43 2013
                start_count = 1
                comp_time = Mon Aug 12 15:19:43 2013


        @param remote_id: E.g. "13133"
        @param stdout: list of lines
        @param stderr: list of lines
        @return:
        """
        logger.debug("stdout = %s\nstderr= %s" % (stdout, stderr))
        qstat_result = TorqueQStatResult()
        qstat_result.remote_id = remote_id
        prefix = remote_id + "."
        logger.debug("prefix = %s" % prefix)
        job_state = None

        if len(stderr) > 0:
            if any(['Unknown Job' in line for line in stderr]):
                qstat_result.status = TorqueQStatResult.JOB_NOT_FOUND
                return qstat_result
        matched_job = False
        for line in stdout:
            line = line.strip()
            logger.debug("parsing qstat: [%s]" % line)
            if line.startswith("Job Id:"):
                if prefix in line:
                    matched_job = True

            elif matched_job and line.startswith("job_state"):
                job_state = self._parse_qstat_line(line)
        if not matched_job:
            qstat_result.status = TorqueQStatResult.JOB_NOT_FOUND
            return qstat_result

        assert job_state in TorqueParser.POSSIBLE_STATES, \
            "Job state is wrong. Expected: %s Actual: %s" % (TorqueParser.POSSIBLE_STATES, job_state)

        if job_state in TorqueParser.FINISHED_STATES:
            qstat_result.status = TorqueQStatResult.JOB_COMPLETED
            return qstat_result
        elif job_state in TorqueParser.RUNNING_STATES:
            qstat_result.status = TorqueQStatResult.JOB_RUNNING
            return qstat_result
        else:
            raise Exception("Unknown job state: %s" % job_state)

    def _get_job_status(self, qstat_line):
        """
        @param qstat_line:
        @return: status

        NB. Possible statuses:
            C   Job is completed after having run
            E   Job is exiting after having run.
            H   Job is held.
            Q   job is queued, eligible to run or routed.
            R   job is running.
            T   job is being moved to new location.
            W   job is waiting for its execution time (-a option) to be reached.
            S   (Unicos only) job is suspended.
            see http://www.clusterresources.com/torquedocs21/commands/qstat.shtml
        """
        parts = qstat_line.split()
        job_status = parts[TorqueParser.QSTAT_JOB_STATE_INDEX]
        return job_status

    def parse_abort(self, remote_id, exit_code, stdout, stderr):
        result = TorqueQDelResult()
        if exit_code == 0:
            result.status = TorqueQDelResult.JOB_ABORTED
            return result

        if 'invalid state for job - COMPLETE' in "\n".join(stderr):
            result.status = TorqueQDelResult.JOB_FINISHED
            return result

        result.status = TorqueQDelResult.JOB_ABORTION_ERROR
        result.error = "\n".join(stderr)

        return result
