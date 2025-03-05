# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import contextlib
import io
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

    def test_simple_with_dumps(self):
        script = """
            import coredumpy
            def g(arg):
                with open("coredumpy_dump.json", "w") as f:
                    f.write(coredumpy.dumps())
                return arg
            def f():
                x = 142857
                y = [3, {'a': [4, None]}]
                g(y)
            f()
        """
        stdout, _ = self.run_test(script, "coredumpy_dump.json", [
            "w",
            "p arg",
            "u",
            "p x",
            "q"
        ])

        self.assertIn("-> f()", stdout)
        self.assertIn("script.py(11)<module>", stdout)
        self.assertIn("-> g(y)", stdout)
        self.assertIn("script.py(5)g()", stdout)
        self.assertIn("[3, {'a': [4, None]}]", stdout)
        self.assertIn("142857", stdout)

    def test_depth(self):
        script = """
            import coredumpy
            def f():
                x = 142857
                y = [3, {'a': [4, None]}]
                coredumpy.dump(path="coredumpy_dump", depth=1)
            f()
        """
        stdout, _ = self.run_test(script, "coredumpy_dump", [
            "p x",
            "p y"
        ])

        self.assertIn("[3, <Unknown Object>]", stdout)
        self.assertIn("142857", stdout)

    def test_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            child_dir = os.path.join(tmpdir, "child")
            script = f"""
                import coredumpy
                coredumpy.dump(directory={repr(tmpdir)})
                coredumpy.dump(directory={repr(tmpdir)})
                coredumpy.dump(directory={repr(child_dir)})
            """
            self.run_script(script)
            self.assertEqual(len(os.listdir(tmpdir)), 3)
            self.assertEqual(len(os.listdir(child_dir)), 1)

    def test_conf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                cwd = os.getcwd()
                os.chdir(tmpdir)

                with open("conf_coredumpy.py", "w") as f:
                    f.write("print('hello world')")

                script = """
                    import coredumpy
                    def f():
                        coredumpy.dump(path="coredumpy_dump")
                    f()
                """
                stdout, _ = self.run_test(script, "coredumpy_dump", [
                    "q"
                ])

                self.assertIn("hello world", stdout)

                stdout, _ = self.run_script("import coredumpy")
                self.assertIn("hello world", stdout)

                from coredumpy.conf_hook import startup_conf
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    startup_conf()
                self.assertIn("hello world", buf.getvalue())
            finally:
                os.chdir(cwd)

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

    def test_cli(self):
        script = """
            def g(arg):
                return 1 / arg
            def f(x):
                a = 142857
                g(x)
            f(0)
        """
        stdout, _ = self.run_test(script, "coredumpy_dump", [
            "w",
            "p arg",
            "u",
            "p a",
            "q"
        ], use_cli_run=True)

        self.assertIn("-> f(0)", stdout)
        self.assertIn("-> g(x)", stdout)
        self.assertIn("142857", stdout)

    def test_json(self):
        script = """
            x = 3
            raise ValueError("test")
        """

        stdout, _ = self.run_test(script, "coredumpy_dump.json", [
            "p x + 3",
            "q"
        ], use_cli_run=True)

        self.assertIn("6", stdout)

    def test_cli_invalid(self):
        stdout, _ = self.run_run([])
        self.assertIn("Error", stdout)

        stdout, _ = self.run_run(["notexist.py"])
        self.assertIn("Error", stdout)

        stdout, _ = self.run_run([os.path.dirname(__file__)])
        self.assertIn("Error", stdout)

        stdout, _ = self.run_run(["-m", "nonexistmodule"])
        self.assertIn("Error", stdout)

    def test_peek(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = f"""
                import coredumpy
                coredumpy.dump(description="test", directory={repr(tmpdir)})
            """
            script_json = f"""
                import coredumpy
                coredumpy.dump(description="test", path={repr(os.path.join(tmpdir, "dump.json"))})
            """
            self.run_script(script)
            self.run_script(script)
            self.run_script(script_json)
            with open(os.path.join(tmpdir, "invalid"), "w") as f:
                f.write("{invalid}")

            self.assertEqual(len(os.listdir(tmpdir)), 4)
            stdout, _ = self.run_peek([tmpdir])
            stdout2, _ = self.run_peek([os.path.join(tmpdir, file) for file in os.listdir(tmpdir)])

            self.assertEqual(stdout, stdout2)

            stdout, _ = self.run_peek([os.path.join(tmpdir, "nosuchfile")])
            self.assertIn("not found", stdout)

    def test_nonexist_file(self):
        stdout, stderr = self.run_test("", "nonexist_dump", [])
        self.assertIn("File nonexist_dump not found", stdout)
