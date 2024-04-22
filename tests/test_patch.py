# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


from .base import TestBase


class TestPatch(TestBase):
    def test_inspect(self):
        script = """
            import inspect
            from coredumpy.patch import patch_all
            patch_all()
            class FakeFrame:
                def __init__(self):
                    self._coredumpy_type = "frame"
            class FakeCode:
                def __init__(self):
                    self._coredumpy_type = "code"
            assert inspect.isframe(FakeFrame()), "isframe not patched"
            assert inspect.iscode(FakeCode()), "iscode not patched"
            print("patch inspect success")
        """

        stdout, stderr = self.run_script(script)
        self.assertIn("patch inspect success", stdout, stderr)
