# -*- coding: utf-8 -*-

import TaskManager

Tasks = TaskManager.TaskManager()

from Tasklets import tasklets

from conf import config

def startup():
    """Start up the TaskManager, so it can go and get some jobs..."""
    print "Starting TaskManager..."
    Tasks.start()
    
    # load up saved tasklets
    print "Loading Tasks..."
    tasklets.load()
    
def shutdown():
    """pickle tasks to disk"""
    tasklets.save(directory=config.config['backend']['tasklets'])