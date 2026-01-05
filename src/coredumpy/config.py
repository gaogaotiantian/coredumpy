# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import contextlib
import os
import re
from types import GenericAlias
from typing import Callable


class _Config:
    default_recursion_depth: int
    dump_timeout: int
    dump_all_threads: bool
    hide_secret: bool
    secret_patterns: list[re.Pattern]
    hide_environ: bool
    environ_filter: Callable

    def __init__(self) -> None:
        self.default_recursion_depth = 10
        self.dump_timeout = 60
        self.dump_all_threads = True
        self.hide_secret = True
        self.secret_patterns = [
            re.compile(r"[A-Za-z0-9]{32,1024}")
        ]
        self.hide_environ = True
        self._environ_values: set[str] = set()
        self.environ_filter = lambda env: len(env) > 8

    def __setattr__(self, name: str, value: object) -> None:
        annotated_type = type(self).__annotations__.get(name)
        if annotated_type is not None:
            if isinstance(annotated_type, GenericAlias):
                # Handle generic types like List, Dict, etc.
                assert isinstance(annotated_type.__origin__, type)
                if not isinstance(value, annotated_type.__origin__):
                    raise ValueError(f"Expected type {annotated_type} for {name}, got {type(value)}")
            elif not isinstance(value, annotated_type):
                raise ValueError(f"Expected type {annotated_type} for {name}, got {type(value)}")
        super().__setattr__(name, value)

    @property
    def environ_values(self) -> set[str]:
        return self._environ_values

    @contextlib.contextmanager
    def dump_context(self):
        if self.hide_environ:
            self._environ_values = set(env for env in os.environ.values() if self.environ_filter(env))
        yield
        self._environ_values = set()


config = _Config()
