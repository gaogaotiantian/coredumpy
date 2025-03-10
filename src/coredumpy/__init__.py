# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


__version__ = "0.3.0"

import coredumpy.pytest_hook as pytest_hook
from .coredumpy import Coredumpy, dump, dumps, load
from .except_hook import patch_except
from .main import main
from .type_support import TypeSupportBase, TypeSupportContainerBase, NotReady
from .unittest_hook import patch_unittest
from .conf_hook import startup_conf

startup_conf()


__all__ = [
    "Coredumpy",
    "dump",
    "dumps",
    "load",
    "main",
    "patch_except",
    "patch_unittest",
    "pytest_hook",
    "TypeSupportBase",
    "TypeSupportContainerBase",
    "NotReady",
]
