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

"""
Configuration
=============
follows a path, reading in config files. Overlays their settings on top of a default, on top of each other.
then stores the config in a sanitised form in a hash of hashes, inside the object.

Yabi then asks for various settings when it needs them
"""

import ConfigParser
import os.path
import re
import StringIO
import urlparse

re_url_schema = re.compile(r'\w+')

import syslog

syslog_facilities = {
    'LOG_KERN': syslog.LOG_KERN,
    'LOG_USER': syslog.LOG_USER,
    'LOG_MAIL': syslog.LOG_MAIL,
    'LOG_DAEMON': syslog.LOG_DAEMON,
    'LOG_AUTH': syslog.LOG_AUTH,
    'LOG_LPR': syslog.LOG_LPR,
    'LOG_NEWS': syslog.LOG_NEWS,
    'LOG_UUCP': syslog.LOG_UUCP,
    'LOG_CRON': syslog.LOG_CRON,
    'LOG_SYSLOG': syslog.LOG_SYSLOG,
    'LOG_LOCAL0': syslog.LOG_LOCAL0,
    'LOG_LOCAL1': syslog.LOG_LOCAL1,
    'LOG_LOCAL2': syslog.LOG_LOCAL2,
    'LOG_LOCAL3': syslog.LOG_LOCAL3,
    'LOG_LOCAL4': syslog.LOG_LOCAL4,
    'LOG_LOCAL5': syslog.LOG_LOCAL5,
    'LOG_LOCAL6': syslog.LOG_LOCAL6,
    'LOG_LOCAL7': syslog.LOG_LOCAL7
}


def parse_url(uri):
    """Parse a url via the inbuilt urlparse. But this is slightly different
    as it can handle non-standard schemas. returns the schema and then the
    tuple from urlparse"""
    uri = uri.strip()
    scheme, rest = uri.split(":", 1)
    assert re_url_schema.match(scheme)
    return scheme, urlparse.urlparse(rest)

SEARCH_PATH = [
    "~/.yabi/yabi.conf",
    "~/.yabi/backend/yabi.conf",
    "~/yabi.conf",
    "~/.yabi",
    "/etc/yabi.conf",
    "/etc/yabi/yabi.conf"
]

##
## Support functions that do some text processing
##


def port_setting(port):
    """returns ip,port or raises exception if error"""
    if type(port) is tuple:
        return port

    re_port = re.compile(r'^(\d+\.\d+\.\d+\.\d+)(:\d+)?$')
    result = re_port.search(port)
    if result:
        ip = result.group(1)
        port = int(result.group(2)[1:]) if result.group(2) else 8000
        return ip, port
    try:
        if str(int(port)) == port:
            return '0.0.0.0', int(port)
    except ValueError:
        raise Exception("malformed IP:port setting")


def email_setting(email):
    """process an email of the form "First Last <email@server.com>" into name and email.
    also handle just plain email address with no name
    """
    import rfc822
    return rfc822.parseaddr(email)


# process boolean string into python boolean type
boolean_proc = lambda x: x if type(x) is bool else x.lower() == "true" or x.lower() == "t" or x.lower() == "yes" or x.lower() == "y"


def path_sanitise(path):
    return os.path.normpath(os.path.expanduser(path))


class ConfigError(Exception):
    pass


##
## The Configuration store. Singleton.
##
class Configuration(object):
    """Holds the running configuration for the full yabi stack that is running under this twistd"""
    SECTIONS = ['backend']       # sections of the config file
    KEYS = ['port', 'path', 'start_http', 'start_https', 'sslport', 'logfile']

    # defaults
    config = {
        'backend': {
            "port": "0.0.0.0:8000",
            "start_http": True,

            "sslport": "0.0.0.0:8443",
            "start_https": False,

            "path": "/",

            "telnet": False,
            "telnet_port": "0.0.0.0:8021",

            "fifos": None,
            "tasklets": None,
            "temp": "~/.yabi/run/backend/temp/",
            "certificates": None,

            "certfile": "~/.yabi/servercert.pem",
            "keyfile": "~/.yabi/servercert.pem",

            "hmackey": None,

            "admin": None,
            "admin_cert_check": True,

            "syslog_facility": syslog.LOG_DAEMON,
            "syslog_prefix": r"YABI [yabibe:%(username)s]",
        },
        'taskmanager': {
            'polldelay': '5',
            'startup': True,
            "tasktag": None,
            "retrywindow": 60,           # default is to retry for 1 minute. This is for dev and testing. production should up this value.
        },
        'ssh+sge': {
            'qstat': 'qstat',
            'qsub': 'qsub',
            'qacct': 'qacct',
        },
        'execution': {
            'logcommand': 'true',
            'logscripts': 'true'
        },
        'torque': {
            'qstat': 'qstat-torque',
            'qsub': 'qsub-torque',
            'use_sudo': True,
            'sudo': '/usr/bin/sudo',
        },
    }

    def read_defaults(self):
        self.read_from_file(os.path.join(os.path.dirname(__file__), "yabi_defaults.conf"))
        if "YABICONF" in os.environ:
            self.read_from_file(os.path.expanduser(os.environ['YABICONF']))
        else:
            self.read_config()
        self.sanitise()

    def read_from_data(self, dat):
        return self.read_from_fp(StringIO.StringIO(dat))

    def read_from_file(self, filename):
        if os.path.exists(filename) and os.path.isfile(filename):
            print "Loading config file %s" % filename
            return self.read_from_fp(open(filename))
        return None

    def read_from_fp(self, fp):
        conf_parser = ConfigParser.ConfigParser()
        conf_parser.readfp(fp)

        # main sections
        for section in self.SECTIONS:
            if conf_parser.has_section(section):
                # process section

                if section not in self.config:
                    self.config[section] = {}

                for key in self.KEYS:
                    if conf_parser.has_option(section, key):
                        self.config[section][key] = conf_parser.get(section, key)

        # taskmanager section
        name = "taskmanager"
        if conf_parser.has_section(name):
            self.config[name]['polldelay'] = conf_parser.get(name, 'polldelay')
            self.config[name]['startup'] = boolean_proc(conf_parser.get(name, 'startup'))
            if conf_parser.has_option(name, 'tasktag'):
                self.config[name]['tasktag'] = conf_parser.get(name, 'tasktag')
            if conf_parser.has_option(name, 'retrywindow'):
                self.config[name]['retrywindow'] = conf_parser.get(name, 'retrywindow')

        # torque section
        name = "torque"
        if conf_parser.has_section(name):
            self.config[name]['qstat'] = conf_parser.get(name, 'qstat')
            self.config[name]['qsub'] = conf_parser.get(name, 'qsub')
            self.config[name]['sudo'] = conf_parser.get(name, 'sudo')
            if conf_parser.has_option(name, 'use_sudo'):
                self.config[name]['use_sudo'] = boolean_proc(conf_parser.get(name, 'use_sudo'))

        # ssh+sge section
        name = "sge+ssh"
        if conf_parser.has_section(name):
            self.config[name]['qstat'] = conf_parser.get(name, 'qstat')
            self.config[name]['qsub'] = conf_parser.get(name, 'qsub')
            self.config[name]['qacct'] = conf_parser.get(name, 'qacct')

        # execution section
        name = "execution"
        if conf_parser.has_section(name):
            for part in ('logcommand', 'logscripts'):
                self.config[name][part] = boolean_proc(conf_parser.get(name, part))

        # backend section
        name = "backend"
        if conf_parser.has_section(name):
            self.config[name]['admin'] = conf_parser.get(name, 'admin')
            if conf_parser.has_option(name, 'fifos'):
                self.config[name]['fifos'] = path_sanitise(conf_parser.get(name, 'fifos'))
            if conf_parser.has_option(name, 'tasklets'):
                self.config[name]['tasklets'] = path_sanitise(conf_parser.get(name, 'tasklets'))
            if conf_parser.has_option(name, 'certificates'):
                self.config[name]['certificates'] = path_sanitise(conf_parser.get(name, 'certificates'))
            if conf_parser.has_option(name, 'temp'):
                self.config[name]['temp'] = path_sanitise(conf_parser.get(name, 'temp'))
            if conf_parser.has_option(name, 'keyfile'):
                self.config[name]['keyfile'] = path_sanitise(conf_parser.get(name, 'keyfile'))
            if conf_parser.has_option(name, 'certfile'):
                self.config[name]['certfile'] = path_sanitise(conf_parser.get(name, 'certfile'))
            if conf_parser.has_option(name, 'hmackey'):
                self.config[name]['hmackey'] = conf_parser.get(name, 'hmackey')
            if conf_parser.has_option(name, 'syslog_facility'):
                self.config[name]['syslog_facility'] = syslog_facilities[conf_parser.get(name, 'syslog_facility').upper()]
            if conf_parser.has_option(name, 'syslog_prefix'):
                self.config[name]['syslog_prefix'] = conf_parser.get(name, 'syslog_prefix').replace('{', r'%(').replace('}', ')s')
            if conf_parser.has_option(name, 'admin_cert_check'):
                self.config[name]['admin_cert_check'] = boolean_proc(conf_parser.get(name, 'admin_cert_check'))

    def read_config(self, search=SEARCH_PATH):
        for part in search:
            self.read_from_file(os.path.expanduser(part))

    def get_section_conf(self, section):
        return self.config[section]

    def sanitise(self):
        """Check the settings for sanity"""
        for section in self.SECTIONS:
            self.config[section]['start_http'] = boolean_proc(self.config[section]['start_http'])
            self.config[section]['start_https'] = boolean_proc(self.config[section]['start_https'])
            self.config[section]['port'] = port_setting(self.config[section]['port'])
            self.config[section]['sslport'] = port_setting(self.config[section]['sslport'])

            conversions = dict(
                telnet=boolean_proc,
                telnetport=port_setting,
                debug=boolean_proc

            )

            for key, value in conversions.iteritems():
                if key in self.config[section]:
                    self.config[section][key] = value(self.config[section][key])

    ##
    ## Methods to gather settings
    ##
    @property
    def yabiadmin(self):
        scheme, rest = parse_url(self.config['backend']['admin'])
        return "%s://%s:%d%s" % (scheme, rest.hostname, rest.port, rest.path)

    @property
    def yabiadminscheme(self):
        return parse_url(self.config['backend']['admin'])[0]

    @property
    def yabiadminserver(self):
        return parse_url(self.config['backend']['admin'])[1].hostname

    @property
    def yabiadminport(self):
        return parse_url(self.config['backend']['admin'])[1].port

    @property
    def yabiadminpath(self):
        return parse_url(self.config['backend']['admin'])[1].path

    @property
    def yabistore(self):
        return "%s:%d%s" % tuple(self.config['store']['port'] + (self.config['store']['path'],))

    ##
    ## classify the settings into a ip/port based classification
    ##
    def classify_ports(self):
        ips = {}
        for section in self.SECTIONS:
            ip, port = self.config[section]['port']

            # ip number
            ipstore = ips[ip] if ip in ips else {}

            # then port
            portstore = ipstore[port] if port in ipstore else {}

            # then path
            path = self.config[section]['path']
            if path in portstore:
                # error. duplicate path
                raise ConfigError("overlapping application paths")

            portstore[path] = section

            ipstore[port] = portstore
            ips[ip] = ipstore

        return ips

config = Configuration()
