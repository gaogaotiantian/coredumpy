# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import importlib
import sys

from coredumpy.py_object_proxy import PyObjectProxy

from .base import TestBase


class TestPyObjectProxy(TestBase):
    def tearDown(self):
        PyObjectProxy.clear()
        return super().tearDown()

    def convert_object(self, obj):
        data = PyObjectProxy.add_object(obj)
        for i, o in PyObjectProxy._objects.items():
            PyObjectProxy.load_object(i, o)
        return PyObjectProxy.load_object(str(id(obj)), data)

    def test_basic(self):
        class A:
            def __init__(self, x):
                self.x = x
        obj = A(142857)
        proxy = self.convert_object(obj)
        self.assertEqual(proxy.x, 142857)
        self.assertEqual(dir(proxy), ['x'])
        self.assertIn('A object at 0x', repr(proxy))

    def test_tuple(self):
        obj = (1, 2, 3)
        proxy = self.convert_object(obj)
        self.assertEqual(proxy, (1, 2, 3))

    def test_set(self):
        obj = {1, 2, 3}
        proxy = self.convert_object(obj)
        self.assertEqual(proxy, {1, 2, 3})

    def test_bool(self):
        obj = True
        proxy = self.convert_object(obj)
        self.assertEqual(proxy, True)

    def test_builtins(self):
        obj = object()
        proxy = self.convert_object(obj)
        self.assertEqual(proxy._coredumpy_type, "object")

    def test_module(self):
        import os
        proxy = self.convert_object(os)
        self.assertEqual(proxy, os)

        # Create a module, then delete the file before converting
        with open("temp_module_for_test.py", "w") as f:
            f.write("pass")

        temp_module_for_test = importlib.import_module("temp_module_for_test")
        data = PyObjectProxy.add_object(temp_module_for_test)

        sys.modules.pop("temp_module_for_test")
        os.remove("temp_module_for_test.py")
        proxy = PyObjectProxy.load_object(str(id(temp_module_for_test)), data)
        self.assertEqual(proxy._coredumpy_type, "module")

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
