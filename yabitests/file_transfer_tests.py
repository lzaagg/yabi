import unittest
from support import YabiTestCase, StatusResult, FileUtils
from fixture_helpers import admin
import os

ONE_GB = 1 * 1024 * 1024 * 1024

class FileUploadTest(YabiTestCase, FileUtils):

    def setUpAdmin(self):
        admin.create_tool_cksum()

    def tearDownAdmin(self):
        from yabiadmin.yabi import models
        models.Tool.objects.get(name='cksum').delete()

    def setUp(self):
        YabiTestCase.setUp(self)
        FileUtils.setUp(self)
        self.setUpAdmin()

    def tearDown(self):
        YabiTestCase.tearDown(self)
        FileUtils.tearDown(self)
        self.tearDownAdmin()

    def test_cksum_of_large_file(self):
        FILESIZE = ONE_GB / 1024
        filename = self.create_tempfile(size=FILESIZE)
        result = self.yabi.run('cksum %s' % filename)
        self.assertTrue(result.status == 0, "Yabish command shouldn't return error!")

        expected_cksum, expected_size = self.run_cksum_locally(filename)

        returned_lines = filter(lambda l: l.startswith(expected_cksum), result.stdout.split("\n"))
        self.assertEqual(len(returned_lines), 1, 'Expected cksum %s result not returned or checksum is incorrect' % expected_cksum)
        our_line = returned_lines[0]
        actual_cksum, actual_size, rest = our_line.split()
        self.assertEqual(expected_cksum, actual_cksum)
        self.assertEqual(expected_size, actual_size)

class FileUploadAndDownloadTest(YabiTestCase, FileUtils):

    def setUpAdmin(self):
        from yabiadmin.yabi import models
        admin.create_tool_dd()

    def tearDownAdmin(self):
        from yabiadmin.yabi import models
        models.Tool.objects.get(name='dd').delete()

    def setUp(self):
        YabiTestCase.setUp(self)
        FileUtils.setUp(self)
        FILESIZE = ONE_GB / 1024
        self.filename = self.create_tempfile(size=FILESIZE)
        self.setUpAdmin()

    def tearDown(self):
        self.tearDownAdmin()
        FileUtils.tearDown(self)
        YabiTestCase.tearDown(self)

    def test_dd(self):
        self._test_dd()

    def test_nolink_nolcopy(self):
        from yabiadmin.yabi import models
        dd = models.Tool.objects.get(name='dd')
        dd.lcopy_supported = False
        dd.link_supported = False
        dd.save()
        self._test_dd()

    def test_nolink_lcopy(self):
        from yabiadmin.yabi import models
        dd = models.Tool.objects.get(name='dd')
        dd.lcopy_supported = True
        dd.link_supported = False
        dd.save()
        self._test_dd()

    def test_link_nolcopy(self):
        from yabiadmin.yabi import models
        dd = models.Tool.objects.get(name='dd')
        dd.lcopy_supported = False
        dd.link_supported = True
        dd.save()
        self._test_dd()

    def _test_dd(self):
        result = self.yabi.run('dd if=%s of=output_file' % self.filename)
        self.assertTrue(result.status == 0, "Yabish command shouldn't return error!")

        expected_cksum, expected_size = self.run_cksum_locally(self.filename)
        copy_cksum, copy_size = self.run_cksum_locally('output_file')
        if os.path.isfile('output_file'):
            os.unlink('output_file')

        self.assertEqual(expected_size, copy_size)
        self.assertEqual(expected_cksum, copy_cksum)

class FileUploadSmallFilesTest(YabiTestCase, FileUtils):

    def setUpAdmin(self):
        from yabiadmin.yabi import models
        admin.create_tool('tar')
        admin.add_tool_to_all_tools('tar')
        tool = models.Tool.objects.get(name='tar')
        tool.accepts_input = True

        value_only = models.ParameterSwitchUse.objects.get(display_text='valueOnly')
        both = models.ParameterSwitchUse.objects.get(display_text='both')
        switch_only = models.ParameterSwitchUse.objects.get(display_text='switchOnly')

        tool_param_c = models.ToolParameter.objects.create(tool=tool, rank=1, switch_use=switch_only, file_assignment = 'none', switch='-c')
        tool_param_f = models.ToolParameter.objects.create(tool=tool, rank=2, switch_use=both, file_assignment = 'none', output_file=True, switch='-f')
        all_files = models.FileType.objects.get(name='all files')
        tool_param_f.accepted_filetypes.add(all_files)
        tool_param_files = models.ToolParameter.objects.create(tool=tool, switch_use=value_only, rank=99, file_assignment = 'all', switch='files')
        tool_param_files.accepted_filetypes.add(all_files)

        tool.save()

    def tearDownAdmin(self):
        from yabiadmin.yabi import models
        models.Tool.objects.get(name='tar').delete()

    def setUp(self):
        YabiTestCase.setUp(self)
        FileUtils.setUp(self)
        self.delete_output_file()
        self.setUpAdmin()

    def tearDown(self):
        self.tearDownAdmin()
        YabiTestCase.tearDown(self)
        FileUtils.tearDown(self)
        self.delete_output_file()

    def delete_output_file(self):
        if os.path.exists('file_1_2_3.tar'):
            os.unlink('file_1_2_3.tar')

    def test_tar_on_a_few_files(self):
        import tarfile
        MB = 1024 * 1024
        dirname = self.create_tempdir() + "/"
        file1 = self.create_tempfile(size=1 * MB, parentdir=dirname)
        file2 = self.create_tempfile(size=2 * MB, parentdir=dirname)
        file3 = self.create_tempfile(size=3 * MB, parentdir=dirname)
        files = dict([(os.path.basename(f), f) for f in (file1, file2, file3)])

        result = self.yabi.run('tar -c -f file_1_2_3.tar %s' % dirname)
        self.assertTrue(result.status == 0, "Yabish command shouldn't return error!")

        extract_dirname = self.create_tempdir()
        tar = tarfile.TarFile('file_1_2_3.tar')
        tar.extractall(extract_dirname)

        tarfiles = tar.getnames()
        self.assertEqual(len(tarfiles), 3)
        for extracted_f in tarfiles:
            full_name = os.path.join(extract_dirname, extracted_f)
            self.assertTrue(os.path.basename(extracted_f) in files, '%s (%s) should be in %s' % (os.path.basename(extracted_f), extracted_f, files))
            matching_f = files[os.path.basename(extracted_f)]
            self.compare_files(matching_f, full_name)

    def compare_files(self, file1, file2):
        expected_cksum, expected_size = self.run_cksum_locally(file1)
        actual_cksum, actual_size = self.run_cksum_locally(file2)
        self.assertEqual(expected_cksum, actual_cksum)
        self.assertEqual(expected_size, actual_size)

