# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


__version__ = "0.0.1"

from .coredumpy import Coredumpy, dump, load
from .except_hook import patch_excepthook
from .main import main
from .type_support import add_supports

add_supports()

__all__ = [
    "Coredumpy",
    "dump",
    "load",
    "main",
    "patch_excepthook",
]