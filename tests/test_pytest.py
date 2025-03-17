# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import os
import tempfile
import textwrap

from .base import TestBase


class TestPytest(TestBase):
    def test_pytest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test = textwrap.dedent("""
                def test_for_pytest_equal():
                    assert 1 == 2

                def test_for_pytest_greater():
                    assert 1 > 2
            """)
            with open(os.path.join(tmpdir, "test.py"), "w") as f:
                f.write(test)

            test_path = os.path.join(tmpdir, "test.py")
            dump_path = os.path.join(tmpdir, "dump")

            script = f"""
                import pytest
                import os
                rootdir = os.path.dirname(__file__)
                pytest.main(["--enable-coredumpy", "--coredumpy-dir", {repr(dump_path)},
                             "--rootdir", rootdir, {repr(test_path)}])
            """
            stdout, stderr = self.run_script(script)
            self.assertEqual(len(os.listdir(dump_path)), 2,
                             f"The dump directory has {os.listdir(dump_path)}\n{stdout}\n{stderr}")

            # Without the enable, it should not produce dumps
            script = f"""
                import pytest
                pytest.main(["--coredumpy-dir", {repr(dump_path)}, {repr(test_path)}])
            """
            self.run_script(script)
            self.assertEqual(len(os.listdir(dump_path)), 2)

    def test_pytest_patch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test = textwrap.dedent("""
                def test_for_pytest_equal():
                    assert 1 == 2

                def test_for_pytest_greater():
                    assert 1 > 2
            """)
            with open(os.path.join(tmpdir, "test.py"), "w") as f:
                f.write(test)

            test_path = os.path.join(tmpdir, "test.py")
            dump_path = os.path.join(tmpdir, "dump")

            script = f"""
                import coredumpy
                import pytest
                import os
                rootdir = os.path.dirname(__file__)
                coredumpy.patch_pytest(directory={repr(dump_path)})
                pytest.main(["--rootdir", rootdir, {repr(test_path)}])
            """
            stdout, stderr = self.run_script(script)
            self.assertEqual(len(os.listdir(dump_path)), 2,
                             f"The dump directory has {os.listdir(dump_path)}\n{stdout}\n{stderr}")
