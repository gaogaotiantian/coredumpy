# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import builtins
import importlib
import sys
import types

from ..config import config
from ..type_support import TypeSupportBase, TypeSupportContainerBase, NotReady


class NoneSupport(TypeSupportBase):
    @classmethod
    def get_type(cls):
        return type(None), "NoneType"

    @classmethod
    def dump(cls, obj):
        return {"type": "NoneType"}, None

    @classmethod
    def load(cls, data, objects):
        return None, None


class BasicTypeSupportBase(TypeSupportBase):
    @classmethod
    def get_type(cls):
        return cls._type, cls._annotation

    @classmethod
    def dump(cls, obj):
        return {"type": cls._annotation, "value": obj}, None

    @classmethod
    def load(cls, data, objects):
        return cls._type(data["value"]), None


class BoolSupport(BasicTypeSupportBase):
    _type = bool
    _annotation = "bool"


class IntSupport(BasicTypeSupportBase):
    _type = int
    _annotation = "int"


class FloatSupport(BasicTypeSupportBase):
    _type = float
    _annotation = "float"


class StrSupport(BasicTypeSupportBase):
    _type = str
    _annotation = "str"

    @classmethod
    def dump(cls, obj):
        if config.hide_environ and obj in config.environ_values:
            obj = "***redacted***"
        elif config.hide_secret:
            for pattern in config.secret_patterns:
                if pattern.match(obj):
                    obj = "***redacted***"
                    break
        return super().dump(obj)


class BytesSupport(TypeSupportBase):
    @classmethod
    def get_type(cls):
        return bytes, "bytes"

    @classmethod
    def dump(cls, obj):
        return {"type": "bytes", "value": obj.hex()}, None

    @classmethod
    def load(cls, data, objects):
        return bytes.fromhex(data["value"]), None


class ListSupport(TypeSupportContainerBase):
    @classmethod
    def get_type(cls):
        return list, "list"

    @classmethod
    def dump(cls, obj: list):
        value = [str(id(item)) for item in obj]
        return {"type": "list", "value": value}, list(obj)

    @classmethod
    def load(cls, data, objects):
        obj = []
        dependency = []
        for item_id in data["value"]:
            if item_id not in objects:
                obj.append(NotReady)
                dependency.append(item_id)
            else:
                obj.append(objects[item_id])
        return obj, dependency

    @classmethod
    def reload(cls, container, data, objects):
        dependency = []
        for i, item_id in enumerate(data["value"]):
            if item_id not in objects:
                dependency.append(item_id)
            else:
                container[i] = objects[item_id]
        return dependency


class TupleSupport(TypeSupportContainerBase):
    @classmethod
    def get_type(cls):
        return tuple, "tuple"

    @classmethod
    def dump(cls, obj: tuple):
        value = [str(id(item)) for item in obj]
        return {"type": "tuple", "value": value}, list(obj)

    @classmethod
    def load(cls, data, objects):
        dependency = [item_id for item_id in data["value"] if item_id not in objects]
        if not dependency:
            return tuple(objects[item_id] for item_id in data["value"]), None
        return NotReady, dependency


class DictSupport(TypeSupportContainerBase):
    @classmethod
    def get_type(cls):
        return dict, "dict"

    @classmethod
    def dump(cls, obj: dict):
        new_objects = []
        value = {}
        for key, val in obj.items():
            value[str(id(key))] = str(id(val))
            new_objects.append(key)
            new_objects.append(val)
        return {"type": "dict", "value": value}, new_objects

    @classmethod
    def load(cls, data, objects):
        dependency = [key_id for key_id in data["value"] if key_id not in objects]
        dependency += [value_id for value_id in data["value"].values() if value_id not in objects]
        if not dependency:
            return {objects[key_id]: objects[value_id] for key_id, value_id in data["value"].items()}, None
        return {}, dependency

    @classmethod
    def reload(cls, container, data, objects):
        dependency = []
        for key_id, value_id in data["value"].items():
            if key_id in objects and value_id in objects:
                container[objects[key_id]] = objects[value_id]
            else:
                if key_id not in objects:
                    dependency.append(key_id)
                if value_id not in objects:
                    dependency.append(value_id)
        return dependency


class SetSupport(TypeSupportContainerBase):
    @classmethod
    def get_type(cls):
        return set, "set"

    @classmethod
    def dump(cls, obj: set):
        value = [str(id(item)) for item in obj]
        return {"type": "set", "value": value}, list(obj)

    @classmethod
    def load(cls, data, objects):
        obj = set()
        dependency = []
        for item_id in data["value"]:
            if item_id not in objects:
                dependency.append(item_id)
            else:
                obj.add(objects[item_id])
        return obj, dependency

    @classmethod
    def reload(cls, container: set, data, objects):
        dependency = []
        for item_id in data["value"]:
            if item_id not in objects:
                dependency.append(item_id)
            else:
                container.add(objects[item_id])
        return dependency


class FrozensetSupport(TypeSupportContainerBase):
    @classmethod
    def get_type(cls):
        return frozenset, "frozenset"

    @classmethod
    def dump(cls, obj: frozenset):
        value = [str(id(item)) for item in obj]
        return {"type": "frozenset", "value": value}, list(obj)

    @classmethod
    def load(cls, data, objects):
        dependency = []
        for item_id in data["value"]:
            if item_id not in objects:
                dependency.append(item_id)
        if not dependency:
            return frozenset(objects[item_id] for item_id in data["value"]), None
        return NotReady, dependency


class ModuleSupport(TypeSupportBase):
    @classmethod
    def get_type(cls):
        return types.ModuleType, "module"

    @classmethod
    def dump(cls, obj: types.ModuleType):
        return {"type": "module", "value": obj.__name__}, None

    @classmethod
    def load(cls, data, objects):
        try:
            module = importlib.import_module(data["value"])
        except ImportError:
            raise NotImplementedError(data["value"])
        return module, None


class FrameLocalsProxySupport(DictSupport):
    @classmethod
    def get_type(cls):
        if sys.version_info < (3, 13):
            raise NotImplementedError()
        return type(sys._getframe().f_locals), "FrameLocalsProxy"

    @classmethod
    def dump(cls, obj):
        obj = dict(obj)
        return DictSupport.dump(obj)


class BuiltinFunctionSupport(TypeSupportBase):
    @classmethod
    def get_type(cls):
        return types.BuiltinFunctionType, "builtin_function"

    @classmethod
    def dump(cls, obj: types.BuiltinFunctionType):
        if obj in builtins.__dict__.values():
            return {"type": "builtin_function", "value": obj.__qualname__}, None
        raise NotImplementedError()

    @classmethod
    def load(cls, data, objects):
        if data["value"] in builtins.__dict__:
            return builtins.__dict__[data["value"]], None
        raise NotImplementedError()


class TypeSupport(TypeSupportBase):
    @classmethod
    def get_type(cls):
        return type, "type"

    @classmethod
    def dump(cls, obj: type):
        if obj in builtins.__dict__.values():
            return {"type": "type", "value": obj.__name__}, None
        raise NotImplementedError()

    @classmethod
    def load(cls, data, objects):
        if data.get("value") in builtins.__dict__:
            return builtins.__dict__[data["value"]], None
        raise NotImplementedError()
