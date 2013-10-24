import logging
import re
from functools import partial

logger = logging.getLogger(__name__)


class SGEQSubResult(object):
    JOB_SUBMITTED = "job submitted"
    JOB_SUBMISSION_ERROR = "job submission error"

    def __init__(self):
        self.status = None
        self.remote_id = None

    def __repr__(self):
        return "qsub result: remote id = %s remote job status = %s" % (self.remote_id, self.status)

class SGEQStatResult(object):
    JOB_RUNNING = "job running"
    JOB_NOT_FOUND = "job not found by qstat"

    def __init__(self):
        self.status = None
        self.remote_id = None

    def __repr__(self):
        return "qstat result: remote id = %s remote job status = %s" % (self.remote_id, self.status)

class SGEQAcctResult(object):
    JOB_COMPLETED = "job succeeded"
    JOB_NOT_FOUND = "job not found by qacct"

    def __init__(self):
        self.status = None
        self.remote_id = None
        self.job_exit_status = None

    def __repr__(self):
        return "qsub result: remote id = %s remote job status = %s exit status = %s" % (self.remote_id, self.status, self.job_exit_status)

class SGEQDelResult(object):
    JOB_ABORTED = "JOB ABORTED"
    JOB_ABORTION_ERROR = "JOB ABORTION ERROR"
    JOB_FINISHED = "JOB FINISHED"

    def __init__(self, status=None, error=None):
        self.status = status
        self.error = error

    @classmethod
    def job_aborted(cls):
        return cls(cls.JOB_ABORTED)

    @classmethod
    def job_finished(cls):
        return cls(cls.JOB_FINISHED)

    @classmethod
    def job_abortion_error(cls, error=None):
        return cls(cls.JOB_ABORTION_ERROR, error)


class SGEParser(object):
    QSUB_JOB_SUBMITTED_PATTERN = r"Your job (?P<remote_id>\d+)"
    QSTAT_JOB_RUNNING_JOB_OUTPUT = r"job_number:\s+(?P<remote_id>\d+)"
    QACCT_JOB_NUMBER = r"^jobnumber\s+(?P<remote_id>\d+)"
    QACCT_EXIT_STATUS = r"^exit_status\s(?P<exit_status>\d+)"
    QACCT_FAILED = r"^failed\s+(?P<failed>[10])"
    QDEL_JOB_ABORTED = r"registered the job (?P<remote_id>\d+) for deletion"
    QDEL_JOB_FINISHED = r'job "(?P<remote_id>\d+)" does not exist'

    def parse_sub(self, stdout, stderr):
        for line in stderr:
            logger.debug("qsub stderr line: %s" % line)
        result = SGEQSubResult()
        logger.debug("starting qsub parse..")
        for line in stdout:
            logger.debug("parsing qsub stdout line: %s" % line)
            m = re.match(SGEParser.QSUB_JOB_SUBMITTED_PATTERN, line)
            if m:
                logger.debug("matched remote id!")
                result.remote_id = m.group("remote_id")
                result.status = SGEQSubResult.JOB_SUBMITTED
                return result

        result.status = SGEQSubResult.JOB_SUBMISSION_ERROR
        logger.debug("parse result = %s" % result)
        return result

    def parse_poll(self, remote_id, stdout, stderr):
        result = SGEQStatResult()
        for line in stdout:
            logger.debug("parsing qstat stdout line: %s" % line)
            m = re.match(SGEParser.QSTAT_JOB_RUNNING_JOB_OUTPUT, line)
            if m:
                logger.debug("matched remote id!")
                if m.group("remote_id") == remote_id:
                    result.status = result.JOB_RUNNING
                    return result

        result.status = result.JOB_NOT_FOUND
        logger.debug("parse result = %s" % result)
        return result

    def parse_qacct(self, remote_id, stdout, stderr):
        result = SGEQAcctResult()
        found_job = False
        for line in stdout:
            logger.debug("parsing qacct stdout line: %s" % line)
            m = re.match(SGEParser.QACCT_JOB_NUMBER, line)
            if m:
                logger.debug("matched job number!")
                if m.group("remote_id") != remote_id:
                    raise Exception("Error parsing qacct result: Expected remote_id %s Actual %s" % (remote_id, m.group("remote_id")))
                else:
                    found_job = True
                    result.remote_id = m.group("remote_id")
                    result.status = SGEQAcctResult.JOB_COMPLETED

        if not found_job:
            result.status = SGEQAcctResult.JOB_NOT_FOUND

        return result

    def parse_abort(self, remote_id, stdout, stderr):
        # Note: SGE tools print errors to stdout
        result = SGEQDelResult()
        for line in stdout:
            if job_aborted_line(line, remote_id):
                return SGEQDelResult.job_aborted()

            if job_finished_line(line, remote_id):
                return SGEQDelResult.job_finished()

        return SGEQDelResult.job_abortion_error("\n".join(stdout))


def line_matches(regex, line, remote_id):
    m = re.search(regex, line)
    if m:
        if m.group("remote_id") != remote_id:
            raise Exception("Error parsing qdel result: Expected remote_id %s Actual %s" % (remote_id, m.group("remote_id")))
        return True
    return False

job_aborted_line = partial(line_matches, SGEParser.QDEL_JOB_ABORTED)
job_finished_line = partial(line_matches, SGEParser.QDEL_JOB_FINISHED) 

