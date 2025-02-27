# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import sys

from coredumpy.py_object_container import PyObjectContainer
from coredumpy.type_support import TypeSupportBase

from .base import TestBase


class TestTypeSupport(TestBase):
    def test_lazy_load(self):
        import coredumpy.types.stdlib_types  # noqa: F401
        self.assertIsNone(sys.modules.get("decimal"))
        import decimal
        d = decimal.Decimal('3.14')
        container = PyObjectContainer()
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
