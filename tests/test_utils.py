# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import os

from coredumpy.utils import get_dump_filename

from .base import TestBase


class FakeCode:
    def __init__(self, name):
        self.co_name = name


class FakeFrame:
    def __init__(self, name):
        self.f_code = FakeCode(name)
        self.f_lineno = 1


class TestUtils(TestBase):
    def test_get_dump_filename(self):
        frame = FakeFrame("test_get_dump_filename")
        filename = get_dump_filename(frame, None, None)
        self.assertEqual(filename, os.path.abspath(filename))
        self.assertIn("test_get_dump_filename_1", filename)

        filename = get_dump_filename(frame, "test.dump", None)
        self.assertEqual(filename, os.path.abspath("test.dump"))

        filename = get_dump_filename(frame, lambda: "test.dump", None)
        self.assertEqual(filename, os.path.abspath("test.dump"))

        filename = get_dump_filename(frame, None, "dir")
        self.assertEqual(filename, os.path.abspath(filename))
        self.assertIn("test_get_dump_filename_1", filename)
        self.assertIn("dir", filename)

        with self.assertRaises(ValueError):
            filename = get_dump_filename(frame, "test.dump", "dir")

    def test_escape_name(self):
        frame = FakeFrame("<module>")
        filename = get_dump_filename(frame, None, None)
        self.assertNotIn("<", filename)
        self.assertNotIn(">", filename)
