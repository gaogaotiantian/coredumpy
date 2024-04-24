# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import importlib
import types

from .py_object_proxy import PyObjectProxy


def module_encoder(obj):
    return {"type": "module", "value": obj.__name__}


def module_decoder(id, data):
    try:
        return importlib.import_module(data["value"])
    except ImportError:
        return PyObjectProxy.default_decode(id, data)


def add_supports():
    PyObjectProxy.add_support(types.ModuleType, "module", module_encoder, module_decoder)
