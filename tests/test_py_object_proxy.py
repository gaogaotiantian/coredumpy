# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


from coredumpy.py_object_proxy import PyObjectProxy
from coredumpy.py_object_container import PyObjectContainer

from .base import TestBase


class TestPyObjectProxy(TestBase):
    def test_basic(self):
        proxy = PyObjectProxy()
        proxy._coredumpy_type = "A"
        proxy._coredumpy_id = 142857
        self.assertEqual(repr(proxy), "<A object at 0x22e09>")

    def test_container(self):
        proxy = PyObjectProxy()
        proxy._coredumpy_type = "A"
        proxy._coredumpy_id = 142857

        with self.assertRaises(RuntimeError):
            proxy.x

        container = PyObjectContainer()
        proxy.link_container(container)

        with self.assertRaises(AttributeError):
            proxy.x

        o = 123456
        proxy.set_coredumpy_attr("x", str(id(o)))
        container.add_object(o)
        container.load_objects(container.get_objects())
        self.assertEqual(proxy.x, o)

    def test_attr(self):
        proxy = PyObjectProxy()
        proxy._coredumpy_type = "A"
        proxy._coredumpy_id = 142857

        container = PyObjectContainer()
        proxy.link_container(container)

        proxy.x = 3
        proxy.set_coredumpy_attr("y", str(id(proxy.x)))
        container.add_object(proxy.x)
        container.load_objects(container.get_objects())

        self.assertEqual(proxy.x, 3)
        self.assertEqual(proxy.y, 3)

        with self.assertRaises(AttributeError):
            proxy.z
