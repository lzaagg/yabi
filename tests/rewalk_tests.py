# Yabi - a sophisticated online research environment for Grid, High Performance and Cloud computing.
# Copyright (C) 2015  Centre for Comparative Genomics, Murdoch University.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
from .support import YabiTestCase, StatusResult, FileUtils, all_items, json_path
from .fixture_helpers import admin
import os
import shutil
from datetime import datetime

class RewalkTest(YabiTestCase, FileUtils):
    '''
    This test creates a worflow that dd's a file and then cksum the file produced by dd.
    The cksum will have a dependency on the dd and it will have to be re-walked by Yabi.
    Yabish doesn't support workflows with multiple jobs, so we will have to submit the json directly.
    Furthermore, the we will use has to be created in the /home/dir of the user so that the BE can access it.
    In order to make this all work on different machines/users we will replace variables in the JSON file at run time.
    '''
    TIMEOUT = 60.0 * 20.0

    def setUpAdmin(self):
        admin.create_tool_cksum(testcase=self)
        admin.create_tool_dd(testcase=self)

    def setUp(self):
        YabiTestCase.setUp(self)
        FileUtils.setUp(self)
        self.setUpAdmin()

    def tearDown(self):
        YabiTestCase.tearDown(self)
        FileUtils.tearDown(self)

    def get_localfs_dir(self):
        LOCALFS_PREFIX = 'localfs://demo@localhost'
        result = self.yabi.run(['ls'])
        clean = result.stdout.splitlines()[0]
        index = clean.rfind(LOCALFS_PREFIX)
        assert result.status == 0, "yabi ls returned an error"
        assert index >= 0, "didn't find line starting with localfs in output of yabi ls"
        return clean[index+len(LOCALFS_PREFIX):]

    def prepare_json(self, filename, new_filename, variables):
        '''Takes contents of filename replaces the variables in it and writes it out to new_filename'''
        content = None
        with open(filename) as f:
            content = f.read()

        changed_content = content
        for k,v in variables.items():
            changed_content = changed_content.replace("${%s}" % k, v)

        with open(new_filename, 'w') as f :
            f.write(changed_content)

    def test_dd_file_then_cksum_direct_json(self):
        wfl_json_file = json_path('dd_then_cksum')
        localfs_dir = self.get_localfs_dir()

        ONE_MB = 1024 * 1024
        filename = self.create_tempfile(size=ONE_MB)
        shutil.copy(filename, localfs_dir)
        filename = os.path.join(localfs_dir, os.path.basename(filename))
        self.delete_on_exit(filename)

        changed_json_file = os.path.join(localfs_dir, 'dd_then_cksum.json')

        self.delete_on_exit(changed_json_file)

        self.prepare_json(wfl_json_file, changed_json_file, {
            'DIR': localfs_dir, 'FILENAME': os.path.basename(filename),
            'NOW': datetime.now().strftime("%Y-%m-%d %H-%M-%S")})

        result = self.yabi.run(['submitworkflow', '--backend', 'Local Execution',
                                changed_json_file])
        wfl_id = result.id
        result = StatusResult(self.yabi.run(['status', wfl_id]))
        self.assertEqual(result.workflow.status, 'complete')
        self.assertTrue(all_items(lambda j: j.status == 'complete', result.workflow.jobs))
