# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import inspect
import types
from typing import Callable


class PyObjectProxy:
    _objects: dict[str, dict] = {}
    _proxies: dict[str, object] = {}
    _encoders: dict[str, Callable] = {}
    _decoders: dict[str, Callable] = {}

    def __init__(self):
        self._coredumpy_attrs = {}

    @classmethod
    def clear(cls):
        cls._objects.clear()
        cls._proxies.clear()

    @classmethod
    def add_object(cls, obj):
        if str(id(obj)) not in cls._objects:
            # label the id
            cls._objects[str(id(obj))] = {}
            cls._objects[str(id(obj))] = cls.dump_object(obj)
        return cls._objects[str(id(obj))]

    @classmethod
    def dump_object(cls, obj):
        if obj is None:
            return {"type": "None"}
        elif isinstance(obj, (int, float, str)):
            return {"type": type(obj).__name__, "value": obj}
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                cls.add_object(item)
            return {"type": type(obj).__name__, "value": [str(id(item)) for item in obj]}
        elif isinstance(obj, dict):
            for key, value in obj.items():
                cls.add_object(key)
                cls.add_object(value)
            return {"type": type(obj).__name__, "value": {str(id(key)): str(id(value)) for key, value in obj.items()}}
        elif type(obj) in cls._encoders:
            return cls._encoders[type(obj)](obj)
        return cls.default_encode(obj)

    @classmethod
    def load_object(cls, id, data=None):
        if id in cls._proxies:
            return cls._proxies[id]
        if data is None:
            raise ValueError("Object not found")
        if data["type"] == "None":
            proxy = None
        elif data["type"] in ("int", "float", "str"):
            proxy = data["value"]
        elif data["type"] == "list":
            proxy = [cls.load_object(item_id, cls._objects[item_id]) for item_id in data["value"]]
        elif data["type"] == "tuple":
            proxy = tuple(cls.load_object(item_id, cls._objects[item_id]) for item_id in data["value"])
        elif data["type"] == "set":
            proxy = set(cls.load_object(item_id, cls._objects[item_id]) for item_id in data["value"])
        elif data["type"] == "dict":
            proxy = {cls.load_object(key_id, cls._objects[key_id]):
                     cls.load_object(value_id, cls._objects[value_id])
                     for key_id, value_id in data["value"].items()}
        elif data["type"] in cls._decoders:
            proxy = cls._decoders[data["type"]](id, data)
        else:
            proxy = cls.default_decode(id, data)
        cls._proxies[id] = proxy
        return proxy

    @classmethod
    def load_objects(cls, data):
        cls._objects = data
        for id, obj in data.items():
            cls.load_object(id, obj)

    @classmethod
    def default_encode(cls, obj):
        data = {"type": type(obj).__name__, "attrs": {}}
        if isinstance(obj, (types.ModuleType,
                            types.FunctionType,
                            types.BuiltinFunctionType,
                            types.LambdaType,
                            types.MethodType,
                            )):
            return data
        for attr, value in inspect.getmembers(obj):
            if not attr.startswith("__") and not callable(value):
                cls.add_object(value)
                data["attrs"][attr] = str(id(value))
        return data

    @classmethod
    def default_decode(cls, id, data):
        obj = cls()
        obj._coredumpy_id = id
        obj._coredumpy_type = data["type"]
        for attr, val in data.get("attrs", {}).items():
            setattr(obj, attr, val)
        return obj

    @classmethod
    def add_support(cls, type, type_annotation, encoder, decoder):
        cls._encoders[type] = encoder
        cls._decoders[type_annotation] = decoder

    def __setattr__(self, key, value):
        if key.startswith("_coredumpy_"):
            self.__dict__[key] = value
        else:
            self._coredumpy_attrs[key] = value

    def __getattr__(self, item):
        if item in self._coredumpy_attrs:
            return type(self)._proxies[self._coredumpy_attrs[item]]
        raise AttributeError(f"'{self._coredumpy_type}' object has no attribute '{item}'")

    def __repr__(self):
        return f"<{self._coredumpy_type} object at 0x{int(self._coredumpy_id):x}>"

    def __dir__(self):
        return list(self._coredumpy_attrs.keys())
