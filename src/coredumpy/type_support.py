# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import abc
import inspect
import types
from typing import Callable, Optional, Union


class TypeSupportLazyLoad(Exception):
    pass


class TypeSupportNotImplemented(Exception):
    pass


class NotReady:
    pass


class TypeSupportMeta(abc.ABCMeta):
    def __init__(self, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not name.endswith("Base"):
            TypeSupportManager.add_support(self)


class TypeSupportBase(metaclass=TypeSupportMeta):

    @classmethod
    @abc.abstractmethod
    def get_type(cls) -> tuple[Union[type, Callable], str]:
        ...

    @classmethod
    @abc.abstractmethod
    def dump(cls, obj) -> tuple[dict, Optional[list]]:
        ...

    @classmethod
    @abc.abstractmethod
    def load(cls, data: dict, objects: dict) -> tuple[object, Optional[list[str]]]:
        ...


class TypeSupportContainerBase(TypeSupportBase):

    @classmethod
    @abc.abstractmethod
    def reload(cls, container, data, objects: dict) -> tuple[object, Optional[list[str]]]:
        ...


class TypeSupportManager:
    _encoders: dict = {}
    _decoders: dict = {}
    _lazy_supports: list = []

    @classmethod
    def add_support(cls, support: TypeSupportBase, append_to_lazy_supports=True):
        encode_type, decode_annotation = support.get_type()
        if isinstance(encode_type, type):
            cls._encoders[encode_type] = support
        else:
            cls._lazy_supports.append(support)
        cls._decoders[decode_annotation] = support

    @classmethod
    def load_lazy_supports(cls):
        lazy_supports = []
        for support in cls._lazy_supports:
            encode_type, decode_annotation = support.get_type()
            if isinstance(encode_type, type):
                cls._encoders[encode_type] = support
            else:
                if t := encode_type():
                    cls._encoders[t] = support
                else:
                    lazy_supports.append(support)
        cls._lazy_supports = lazy_supports

    @classmethod
    def dump(cls, obj: object) -> dict:
        if type(obj) in cls._encoders:
            try:
                return cls._encoders[type(obj)].dump(obj)
            except TypeSupportNotImplemented:
                pass
        return cls.default_dump(obj)

    @classmethod
    def load(cls, data, objects):
        typename = data["type"]
        if typename in cls._decoders:
            return cls._decoders[typename].load(data, objects)
        raise TypeSupportNotImplemented()

    @classmethod
    def reload(cls, container, data, objects):
        typename = data["type"]
        if typename in cls._decoders:
            return cls._decoders[typename].reload(container, data, objects)
        raise TypeSupportNotImplemented()

    @classmethod
    def default_dump(cls, obj):
        new_objects = []
        obj_type = type(obj)
        if obj_type.__module__ in ("builtins", "__main__"):
            typename = obj_type.__qualname__
        else:
            typename = f"{obj_type.__module__}.{obj_type.__qualname__}"

        data = {"type": typename}
        if isinstance(obj, (types.ModuleType,
                            types.FunctionType,
                            types.BuiltinFunctionType,
                            types.LambdaType,
                            types.MethodType,
                            )):
            return data, None
        try:
            data["attrs"] = {}
            for attr, value in inspect.getmembers(obj):
                if not attr.startswith("__") and not callable(value):
                    new_objects.append(value)
                    data["attrs"][attr] = str(id(value))
        except Exception:  # pragma: no cover
            # inspect.getmembers may fail on some objects
            pass
        return data, new_objects
