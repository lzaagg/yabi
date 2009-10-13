
import pickle
import os
import dircache
import stackless

from TaskTools import CloseConnections

class Tasklets(object):
    """This is a store for all the tasklets running in back end system. 
    From here they can be saved to disk and reloaded when the server is restarted
    """
    
    def __init__(self):
        self.tasks = []
        
    def add(self, tasklet):
        print "ADD",tasklet
        self.tasks.append(tasklet)
        
    def save(self, directory="/tmp/yabi-tasklets"):
        print "TASKS Save",self.tasks
        
        for task in self.tasks:
            # before we pickle it, if we are waiting on a connection in our stack frame, then set it to have failed
            # so that when we are resurrected in the future, the connection will immediately be marked as failed
            task.remove()
            if hasattr(task,'frame') and task.frame and 'get_failed' in task.frame.f_locals:
                task.frame.f_locals['get_failed'][0]=True
        
        for task in self.tasks:
            print "pickling:",task
            pickled_task = pickle.dumps(task)
            with open(os.path.join(directory,str(id(task))), 'wb') as fh:
                fh.write(pickled_task) 
            
    def load(self,directory="/tmp/yabi-tasklets"):
        self.tasks=[]
            
        for f in dircache.listdir(directory):
            with open(os.path.join(directory,f), 'rb') as fh:
                data = fh.read()
             
            task = pickle.loads(data)
            print "LOAD",f,task
            os.unlink(os.path.join(directory,f))
            
            try:
                task.insert()
                self.tasks.append(task) 
            except RuntimeError, re:
                print "TASK is a dead task. skipping...",re
    
tasklets = Tasklets()