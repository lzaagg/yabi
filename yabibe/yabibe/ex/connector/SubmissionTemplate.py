#!/usr/bin/env python
#
# Mako templating support functions for submission script templating

from mako.template import Template

def make_script(template,working,command,modules,cpus,memory,walltime,yabiusername,username,host,queue,stdout,stderr,tasknum,tasktotal):
    cleaned_template = template.replace('\r\n','\n').replace('\n\r','\n').replace('\r','\n')
    tmpl = Template(cleaned_template)
    
    # our variable space
    variables = {
        'working':working,
        'command':command,
        'modules':modules,
        'cpus':cpus,
        'memory':memory,
        'walltime':walltime,
        'yabiusername':yabiusername,
        'username':username,
        'host':host,
        'queue':queue,
        'stdout':stdout,
        'stderr':stderr,
        'tasknum':tasknum,
        'tasktotal':tasktotal,
        'arrayid':tasknum,
        'arraysize':tasktotal
    }
    
    return str(tmpl.render(**variables))