# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import inspect
import queue
import types
from typing import Callable

from .type_support import TypeSupportManager, TypeSupportNotImplemented, NotReady
from .types import builtin_types  # noqa: F401


class _Unknown:
    def __repr__(self):
        return "<Unknown Object>"


_unknown = _Unknown()


class PyObjectProxy:
    _objects: dict[str, dict] = {}
    _proxies: dict[str, object] = {}
    _encoders: dict[str, Callable] = {}
    _decoders: dict[str, Callable] = {}
    _pending_objects: queue.Queue = queue.Queue()
    _current_recursion_depth = 0
    _max_recursion_depth = 100

    def __init__(self):
        self._coredumpy_attrs = {}

    @classmethod
    def clear(cls):
        cls._objects.clear()
        cls._proxies.clear()

    @classmethod
    def add_object(cls, obj):
        TypeSupportManager.load_lazy_supports()
        objects = {}
        curr_recursion_depth = 0
        pending_objects = [obj]
        while curr_recursion_depth < cls._max_recursion_depth and pending_objects:
            next_objects = {}
            for o in pending_objects:
                data, new_objects = TypeSupportManager.dump(o)
                objects[str(id(o))] = data
                if new_objects:
                    for new_obj in new_objects:
                        if str(id(new_obj)) not in objects:
                            next_objects[str(id(new_obj))] = new_obj
            curr_recursion_depth += 1
            pending_objects = list(next_objects.values())
        cls._objects.update(objects)
        return cls._objects[str(id(obj))]

    @classmethod
    def load_objects(cls, objects):
        TypeSupportManager.load_lazy_supports()
        cls._objects = objects.copy()
        unresolved_queue = queue.Queue()
        not_ready_objects = set()
        for key in cls._objects:
            unresolved_queue.put(key)

        while not unresolved_queue.empty():
            obj_id = unresolved_queue.get()
            data = cls._objects.get(obj_id)
            if data is None:
                proxy = _unknown
            else:
                if obj_id in cls._proxies:
                    if obj_id in not_ready_objects:
                        dependency = TypeSupportManager.reload(cls._proxies[obj_id], data, cls._proxies)
                        if dependency:
                            for dep_id in dependency:
                                unresolved_queue.put(dep_id)
                        else:
                            not_ready_objects.remove(obj_id)
                    continue
                else:
                    try:
                        proxy, dependency = TypeSupportManager.load(data, cls._proxies)
                        if dependency:
                            not_ready_objects.add(obj_id)
                            for dep_id in dependency:
                                unresolved_queue.put(dep_id)
                            unresolved_queue.put(obj_id)
                        else:
                            if obj_id in not_ready_objects:
                                not_ready_objects.remove(obj_id)
                    except TypeSupportNotImplemented:
                        proxy = cls.default_decode(obj_id, data)

            if proxy is not NotReady:
                cls._proxies[obj_id] = proxy

    @classmethod
    def get_object(cls, obj_id):
        return cls._proxies.get(obj_id, _unknown)

    @classmethod
    def default_encode(cls, obj):
        obj_type = type(obj)
        if obj_type.__module__ in ("builtins", "__main__"):
            typename = obj_type.__qualname__
        else:
            typename = f"{obj_type.__module__}.{obj_type.__qualname__}"

        data = {"type": typename, "attrs": {}}
        if isinstance(obj, (types.ModuleType,
                            types.FunctionType,
                            types.BuiltinFunctionType,
                            types.LambdaType,
                            types.MethodType,
                            )):
            return data
        try:
            for attr, value in inspect.getmembers(obj):
                if not attr.startswith("__") and not callable(value):
                    cls._add_object(value)
                    data["attrs"][attr] = str(id(value))
        except Exception:  # pragma: no cover
            # inspect.getmembers may fail on some objects
            pass
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
