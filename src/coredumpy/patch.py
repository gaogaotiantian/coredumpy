# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import inspect
import types


def isframe(obj):
    return isinstance(obj, types.FrameType) or getattr(obj, "_coredumpy_type", None) == "frame"


def iscode(obj):
    return isinstance(obj, types.CodeType) or getattr(obj, "_coredumpy_type", None) == "code"


def patch_all():
    inspect.isframe = isframe
    inspect.iscode = iscode
