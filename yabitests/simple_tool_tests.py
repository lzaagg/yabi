import unittest
from support import YabiTestCase, StatusResult, all_items, json_path
from fixture_helpers import admin
import os
import time

class HostnameTest(YabiTestCase):

    def setUp(self):
        YabiTestCase.setUp(self)
        admin.create_tool('hostname')
        admin.add_tool_to_all_tools('hostname') 

    def tearDown(self):
        from yabiadmin.yabi import models
        models.Tool.objects.get(name='hostname').delete()
        YabiTestCase.tearDown(self)

    def test_hostname(self):
        from socket import gethostname
        result = self.yabi.run(['hostname'])
        self.assertTrue(gethostname() in result.stdout)

    def test_submit_json_directly(self):
        from socket import gethostname
        result = self.yabi.run(['submitworkflow', json_path('hostname')])
        self.assertTrue(gethostname() in result.stdout)

    def test_submit_json_directly_larger_workflow(self):
        result = self.yabi.run(['submitworkflow', json_path('hostname_hundred_times')])
        # doesn't cause problems with this    
        #result = self.yabi.run(['submitworkflow', json_path('hostname_five_times')])
        wfl_id = result.id

        result = StatusResult(self.yabi.run(['status', wfl_id]))

        print result.status
        print result.workflow

        self.assertEqual(result.workflow.status, 'complete')
        self.assertTrue(all_items(lambda j: j.status == 'complete', result.workflow.jobs))

class ExplodingBackendTest(YabiTestCase):

    def setUp(self):
        YabiTestCase.setUp(self)
        admin.create_exploding_backend()
        admin.create_tool('hostname', backend_name='Exploding Backend')
        admin.add_tool_to_all_tools('hostname') 

    def tearDown(self):
        from yabiadmin.yabi import models
        models.Tool.objects.get(name='hostname').delete()
        models.Backend.objects.get(name='Exploding Backend').delete()
        YabiTestCase.tearDown(self)

    def test_hostname(self):
        from socket import gethostname
        result = self.yabi.run(['hostname'])
        self.assertTrue('Error running workflow' in result.stderr)

    def test_submit_json_directly_larger_workflow(self):
        result = self.yabi.run(['submitworkflow', json_path('hostname_hundred_times')])
        # doesn't cause problems with this    
        #result = self.yabi.run(['submitworkflow', json_path('hostname_five_times')])
        wfl_id = result.id
        all_jobs_finished = False
        while not all_jobs_finished:
            result = StatusResult(self.yabi.run(['status', wfl_id]))
            all_jobs_finished = all_items(lambda j: j.status in ('error', 'complete'), result.workflow.jobs)
            time.sleep(2)

        self.assertEqual(result.workflow.status, 'error')
        self.assertTrue(all_items(lambda j: j.status == 'error', result.workflow.jobs))
