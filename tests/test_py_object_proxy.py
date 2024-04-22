# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


from coredumpy.py_object_proxy import PyObjectProxy

from .base import TestBase


class TestPyObjectProxy(TestBase):
    def tearDown(self):
        PyObjectProxy.clear()
        return super().tearDown()

    def test_basic(self):
        class A:
            def __init__(self, x):
                self.x = x
        obj = A(142857)
        data = PyObjectProxy.add_object(obj)
        for i, o in PyObjectProxy._objects.items():
            PyObjectProxy.load_object(i, o)
        proxy = PyObjectProxy.load_object(str(id(obj)), data)
        self.assertEqual(proxy.x, 142857)
        self.assertEqual(dir(proxy), ['x'])
        self.assertIn('<A object at 0x', repr(proxy))

    def test_nonexist_attr(self):
        class A:
            def __init__(self, x):
                self.x = x
        o = A(142857)
        obj = PyObjectProxy.add_object(o)
        proxy = PyObjectProxy.load_object(str(id(o)), obj)
        with self.assertRaises(AttributeError):
            proxy.y

    def test_invalid(self):
        with self.assertRaises(ValueError):
            PyObjectProxy.load_object("1", None)
