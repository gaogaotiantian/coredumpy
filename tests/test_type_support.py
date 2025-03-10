# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import importlib
import sys

from coredumpy.py_object_container import PyObjectContainer
from coredumpy.py_object_proxy import _unknown
from coredumpy.type_support import is_container, TypeSupportBase

from .base import TestBase


class TestTypeSupport(TestBase):
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

    def test_frozenset(self):
        obj = frozenset([1, 2, 3])
        proxy = self.convert_object(obj)
        self.assertEqual(proxy, frozenset([1, 2, 3]))

    def test_bool(self):
        obj = True
        proxy = self.convert_object(obj)
        self.assertEqual(proxy, True)

    def test_bytes(self):
        obj = b"hello"
        proxy = self.convert_object(obj)
        self.assertEqual(proxy, b"hello")

    def test_cycle(self):
        s = "str"
        lst = [s, s]
        dct = {"key": lst}
        lst.append(dct)
        st = {s}
        t = (st, dct)
        dct["tuple"] = t
        proxy = self.convert_object(t)
        self.assertIs(proxy[0].pop(), proxy[1]["key"][1])
        self.assertIs(proxy, proxy[1]["tuple"])

    def test_multi_container(self):
        test_case = [
            [([([([([])])])])],
            [((((), ()), ()), ())],
            {((((), ()), ()), ())},
            {((((), ()), ()), ()): 1},
        ]

        for obj in test_case:
            proxy = self.convert_object(obj)
            self.assertEqual(proxy, obj)

    def test_builtins(self):
        obj = object()
        proxy = self.convert_object(obj)
        self.assertEqual(proxy._coredumpy_type, "object")

    def test_recursion(self):
        class A:
            _reference = []

            @property
            def parent(self):
                obj = A()
                self._reference.append(obj)
                return obj

        obj = A()
        proxy = self.convert_object(obj)
        for i in range(50):
            self.assertIn("A", proxy._coredumpy_type)
            proxy = proxy.parent

    def test_module(self):
        import os
        proxy = self.convert_object(os)
        self.assertEqual(proxy, os)

        # Create a module, then delete the file before converting
        with open("temp_module_for_test.py", "w") as f:
            f.write("pass")

        temp_module_for_test = importlib.import_module("temp_module_for_test")
        container = PyObjectContainer()
        container.add_object(temp_module_for_test)

        sys.modules.pop("temp_module_for_test")
        os.remove("temp_module_for_test.py")
        container.load_objects(container.get_objects())
        proxy = container.get_object(str(id(temp_module_for_test)))
        self.assertEqual(proxy._coredumpy_type, "module")

    def test_nonexist_attr(self):
        class A:
            def __init__(self, x):
                self.x = x
        o = A(142857)
        proxy = self.convert_object(o)
        with self.assertRaises(AttributeError):
            proxy.y

    def test_nonexist_object(self):
        lst = [0]
        container = PyObjectContainer()
        container.add_object(lst)
        objects = container.get_objects().copy()
        # Made up a non-exist list element
        objects[str(id(lst))]["value"] = ["1234567"]
        container.load_objects(objects)
        self.assertIs(container.get_object(1234567), _unknown)

    def test_invalid(self):
        self.assertEqual(repr(_unknown), "<Unknown Object>")

    def test_lazy_load(self):
        import coredumpy.types.stdlib_types  # noqa: F401
        container = PyObjectContainer()
        sys.modules.pop("decimal", None)
        self.assertIsNone(sys.modules.get("decimal"))
        container.add_object(1)
        import decimal
        d = decimal.Decimal('3.14')
        # decimal.Decimal is not loaded yet
        self.assertFalse(is_container(decimal.Decimal))

        container.add_object(d)
        container.load_objects(container.get_objects())
        self.assertIsInstance(container._proxies[str(id(d))], decimal.Decimal)
        self.assertEqual(container._proxies[str(id(d))], d)

    def test_not_implemented(self):
        class A:
            def __init__(self):
                A.x = 3

        class ASupport(TypeSupportBase):
            @classmethod
            def get_type(cls):
                return A, "tests.test_type_support.A"

            @classmethod
            def dump(cls, obj):
                raise NotImplementedError

            @classmethod
            def load(cls, data, objects):
                raise NotImplementedError

        o = A()
        container = PyObjectContainer()
        container.add_object(o)
        container.load_objects(container.get_objects())
        a = container.get_object(str(id(o)))
        self.assertEqual(a.x, 3)
