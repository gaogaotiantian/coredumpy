# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import types

from .py_object_proxy import PyObjectProxy


def module_encoder(obj):
    return {"type": "_builtin_module", "value": obj.__name__}


def module_decoder(id, data):
    return __import__(data["value"])


def add_supports():
    PyObjectProxy.add_support(types.ModuleType, "_builtin_module", module_encoder, module_decoder)
