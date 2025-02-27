# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import sys

from coredumpy.py_object_proxy import PyObjectProxy

from .base import TestBase


class TestTypeSupport(TestBase):
    def test_lazy_load(self):
        import coredumpy.types.stdlib_types  # noqa: F401
        self.assertIsNone(sys.modules.get("decimal"))
        import decimal
        d = decimal.Decimal('3.14')
        PyObjectProxy.add_object(d)
        PyObjectProxy.load_objects(PyObjectProxy._objects)
        self.assertIsInstance(PyObjectProxy._proxies[str(id(d))], decimal.Decimal)
        self.assertEqual(PyObjectProxy._proxies[str(id(d))], d)
