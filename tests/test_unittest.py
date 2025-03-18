# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import os
import tempfile

from .base import TestBase


class TestUnittest(TestBase):
    def test_unittest_basic(self):
        with tempfile.TemporaryDirectory() as tempdir:
            script = f"""
                import unittest
                from coredumpy import patch_unittest
                patch_unittest(directory={repr(tempdir)})
                class TestUnittest(unittest.TestCase):
                    def test_bool(self):
                        self.assertTrue(False)
                    def test_eq(self):
                        self.assertEqual(1, 2)
                    def test_pass(self):
                        self.assertEqual(1, 1)
                    def test_error(self):
                        raise ValueError()
                unittest.main()
            """
            stdout, stderr = self.run_script(script, expected_returncode=1)
            self.assertIn("FAIL: test_bool", stderr)
            self.assertIn("FAIL: test_eq", stderr)
            self.assertIn("ERROR: test_error", stderr)
            self.assertNotIn("test_pass", stderr)
            self.assertEqual(stdout.count(tempdir), 3)
            self.assertEqual(len(os.listdir(tempdir)), 3)

    def test_unittest_with_cli(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # We don't want to use tests as module because it will conflict
            # with the coredumpy setup for the tests. So we change the cwd
            # here to use data.failed as a module.
            cwd = os.getcwd()
            try:
                base_dir = os.path.dirname(__file__)
                os.chdir(base_dir)
                stdout, stderr = self.run_run(["-m", "unittest", "data.failed",
                                               "--directory", tempdir])
            finally:
                os.chdir(cwd)
            self.assertIn("FAIL: test_bool", stderr)
            self.assertIn("FAIL: test_eq", stderr)
            self.assertIn("ERROR: test_error", stderr)
            self.assertNotIn("test_pass", stderr)
            self.assertEqual(stdout.count(tempdir), 3)
            self.assertEqual(len(os.listdir(tempdir)), 3)
