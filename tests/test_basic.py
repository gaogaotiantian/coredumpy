# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


from .base import TestBase


class TestBasic(TestBase):
    def test_simple(self):
        script = """
            import coredumpy
            def g(arg):
                coredumpy.dump("coredumpy_dump")
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

    def test_except(self):
        script = """
            import coredumpy
            coredumpy.patch_excepthook()
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
