# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import os

from coredumpy.utils import get_dump_filename

from .base import TestBase


class TestUtils(TestBase):
    def test_get_dump_filename(self):
        class FakeFrame:
            def __init__(self, name):
                self.f_code = FakeCode(name)

        class FakeCode:
            def __init__(self, name):
                self.co_name = name

        frame = FakeFrame("test_get_dump_filename")
        filename = get_dump_filename(frame, None, None)
        self.assertTrue(filename.startswith("/"))
        self.assertIn("test_get_dump_filename", filename)

        filename = get_dump_filename(frame, "test.dump", None)
        self.assertEqual(filename, os.path.abspath("test.dump"))

        filename = get_dump_filename(frame, lambda: "test.dump", None)
        self.assertEqual(filename, os.path.abspath("test.dump"))

        filename = get_dump_filename(frame, None, "dir")
        self.assertTrue(filename.startswith("/"))
        self.assertIn("test_get_dump_filename", filename)
        self.assertIn("dir", filename)

        with self.assertRaises(ValueError):
            filename = get_dump_filename(frame, "test.dump", "dir")
