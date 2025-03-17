# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

from .base import TestBase


class TestRegression(TestBase):
    def test_loader(self):
        # __loader__ and __spec__ should not be loaded for security reasons
        script = """
            import coredumpy
            def f():
                coredumpy.dump(path="coredumpy_dump")
            f()
        """
        stdout, _ = self.run_test(script, "coredumpy_dump", [
            "import sys",
            "p sys._getframe().f_globals.get('__loader__', 'loader not found')",
            "p sys._getframe().f_globals.get('__spec__', 'spec not found')",
            "q"
        ])
        self.assertIn("loader not found", stdout)
        self.assertIn("spec not found", stdout)
