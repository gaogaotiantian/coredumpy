# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


__version__ = "0.5.0"

import coredumpy.pytest_hook as pytest_hook
from .config import config
from .coredumpy import Coredumpy, dump, dumps, load
from .except_hook import patch_except
from .main import main
from .pytest_hook import patch_pytest
from .type_support import TypeSupportBase, TypeSupportContainerBase, NotReady
from .unittest_hook import patch_unittest
from .conf_hook import startup_conf
from .types import builtin_types, torch_types  # noqa: F401

startup_conf()


__all__ = [
    "Coredumpy",
    "config",
    "dump",
    "dumps",
    "load",
    "main",
    "patch_except",
    "patch_pytest",
    "patch_unittest",
    "pytest_hook",
    "TypeSupportBase",
    "TypeSupportContainerBase",
    "NotReady",
]
