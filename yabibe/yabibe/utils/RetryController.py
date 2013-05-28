#
# RetryController
#
# this is a class that assists in determining if a subprocess has failed permanently
# or temporarily. It does not deal with success. Only if failures are 'soft' or 'hard'
#

HARD = 1
SOFT = 0

# switch on syslog debugging
DEBUG = False

import re


class RetryController(object):
    default = SOFT                              # when no firm decision can be made, go with this

    hard_exit_codes = []                        # any exit with this code is hard exit

    soft_exit_codes = []                        # any exit with this code is soft exit

    # the format of the following dictionaries
    # key: the exit code
    # value: a list of regular expression matches

    hard_exit_regexps = {}                      # regular expressions to determine finer grained status based on output
    soft_exit_regexps = {}

    def __init__(self):
        self.compile_all_regexps()

    def compile_all_regexps(self):
        self.hard_exit_regexps = self.compile_regexps(self.hard_exit_regexps)
        self.soft_exit_regexps = self.compile_regexps(self.soft_exit_regexps)

    def compile_regexps(self, struct, flags=0):
        out = {}
        for code, regexp_list in struct.iteritems():
            out[code] = []
            for re_item in regexp_list:
                out[code].append(re.compile(re_item, flags))
        return out

    def test(self, exit_code, stderr, logger=None):
        """Test the resturn values from a programme run and return HARD or SOFT

        if logger is passed in, then use it as a callable to report the result of the test.
        This can be set to a method that sends it over HTTP to the middleware
        """
        def dlogger(message):
            if DEBUG:
                print message
            if logger:
                logger(message)

        if exit_code in self.hard_exit_codes:
            dlogger("%s [%d]:'%s' HARD exit based on exit code." % (self.__class__, exit_code, stderr))
            return HARD

        if exit_code in self.soft_exit_codes:
            dlogger("%s [%d]:'%s' SOFT exit based on exit code." % (self.__class__, exit_code, stderr))
            return SOFT

        if exit_code in self.hard_exit_regexps:
            # test regexps
            for regexp in self.hard_exit_regexps[exit_code]:
                match = regexp.search(stderr)
                if match is not None:
                    dlogger("%s [%d]:'%s' HARD exit based on hard exit regexps." % (self.__class__, exit_code, stderr))
                    return HARD

        if exit_code in self.soft_exit_regexps:
            # test regexps
            for regexp in self.soft_exit_regexps[exit_code]:
                match = regexp.search(stderr)
                if match is not None:
                    dlogger("%s [%d]:'%s' SOFT exit based on soft exit regexps." % (self.__class__, exit_code, stderr))
                    return SOFT

        dlogger("%s [%d]:'%s' %s exit based on default." % (self.__class__, exit_code, stderr, "HARD" if self.default == HARD else "SOFT"))
        return self.default


class TorqueQsubRetryController(RetryController):
    default = SOFT
    hard_exit_codes = []

    # any paramiko ssh exceptions will return 255
    soft_exit_codes = [255]

    hard_exit_regexps = {
        2: [
            r'a single - is no a valid option',  # typo exists in error code in torque sourcecode
            r'qsub: illegal -\w value',
            r'qsub: Must be the super user to submit a proxy job',
            r'qsub: -P requires a user name',
            r'qsub: error parsing -\w value',
            r'qsub: illegal -W. job_radix must be',
            r'qsub: DISPLAY not set',
            r'The -J option can only be used in conjunction with -P',
            r'index issues',
            r'qsub: Failed to get xauth data',
            r'qsub: cannot form a valid job name from the script name',
            r'qsub: listen on interactive socket',
            r'qsub: unable to get terminal settings',
            r'qsub: unable to get cwd:',
            r'qsub: cannot chdir to',
            r'qsub: Must be the super user to submit a proxy job',
            r"qsub: User isn't a member of one or more groups",
            r'qsub: Invalid umask value, too many digits',
            r'qsub: invalid .+ value:',
            r'qsub: invalid attribute flag',
            #r'qsub: could not create tmp job file'                 # retry this one so sysadmin can go behind scenes and reconf
        ],
        1: [
            r'qsub: file must be an ascii script',
            r'qsub: Your job has been administratively rejected by the queueing system\.',
            r'qsub: submit filter returned an error code, aborting job submission\.',
            r'qsub: could not open filter o/p',
            r'qsub: unmatched ',
        ],
        3: [
            r'qsub: cannot get \(full\) local host name',
            r'qsub: cannot get full server host name',
        ]
    }


class TorqueQstatRetryController(RetryController):
    default = SOFT
    hard_exit_codes = [2]

    # any paramiko ssh exceptions will return 255
    soft_exit_codes = [1, 255]


class SSHRetryController(RetryController):
    default = SOFT
    hard_exit_codes = []
    soft_exit_codes = []

    hard_exit_regexps = {255: [
        r'Unable to parse key file',
        r'Private key file is encrypted',
        r'not a valid DSA private key file',
        r'Invalid key',
        r'Authentication failed',
        r'Expected name response',
        r'Expected handle',
        r'Expected attributes',
        r'Readlink returned \d+ results',
        r'Realpath returned \d+ results',
        r'size mismatch in put!',
        r'size mismatch in get!',
        r'Remote host key is denied',
        r'certificate verify failed']
    }


class PbsproQsubRetryController(TorqueQsubRetryController):
    pass


class PbsproQstatRetryController(TorqueQstatRetryController):
    pass


class SSHSGEQsubRetryController(TorqueQsubRetryController):
    pass


class SSHSGEQstatRetryController(TorqueQstatRetryController):
    default = SOFT
    hard_exit_codes = [2]
    soft_exit_codes = []

    hard_exit_regexps = {1: [
        "Following jobs do not exist"],
    }


class SSHSGEQacctRetryController(RetryController):
    default = SOFT
    hard_exit_codes = []
    soft_exit_codes = []

    hard_exit_regexps = {1: [
        r"error"],
    }
