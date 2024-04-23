# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import os
import tempfile

from .base import TestBase


class TestBasic(TestBase):
    def test_simple(self):
        script = """
            import coredumpy
            def g(arg):
                coredumpy.dump(path="coredumpy_dump")
                return arg
            def f():
                x = 142857
                y = [3, {'a': [4, None]}]
                g(y)
            f()
        """
        stdout, _ = self.run_test(script, "coredumpy_dump", [
            "w",
            "p arg",
            "u",
            "p x",
            "q"
        ])

        self.assertIn("-> f()", stdout)
        self.assertIn("script.py(10)<module>", stdout)
        self.assertIn("-> g(y)", stdout)
        self.assertIn("script.py(4)g()", stdout)
        self.assertIn("[3, {'a': [4, None]}]", stdout)
        self.assertIn("142857", stdout)

    def test_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            child_dir = os.path.join(tmpdir, "child")
            script = f"""
                import coredumpy
                coredumpy.dump(directory="{tmpdir}")
                coredumpy.dump(directory="{tmpdir}")
                coredumpy.dump(directory="{child_dir}")
            """
            self.run_script(script)
            self.assertEqual(len(os.listdir(tmpdir)), 3)
            self.assertEqual(len(os.listdir(child_dir)), 1)

    def test_except(self):
        script = """
            import coredumpy
            coredumpy.patch_except(path='coredumpy_dump')
            def g(arg):
                return 1 / arg
            g(0)
        """
        stdout, _ = self.run_test(script, "coredumpy_dump", [
            "w",
            "p arg",
            "u",
            "p x",
            "q"
        ])
        self.assertIn("return 1 / arg", stdout)
        self.assertIn("0", stdout)

    def test_nonexist_file(self):
        stdout, stderr = self.run_test("", "nonexist_dump", [])
        self.assertIn("File nonexist_dump not found", stdout)
