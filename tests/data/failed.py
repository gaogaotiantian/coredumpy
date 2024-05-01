# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import unittest


class TestUnittest(unittest.TestCase):
    def test_bool(self):
        self.assertTrue(False)

    def test_eq(self):
        self.assertEqual(1, 2)

    def test_pass(self):
        self.assertEqual(1, 1)

    def test_error(self):
        raise ValueError()
