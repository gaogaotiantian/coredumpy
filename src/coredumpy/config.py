# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import contextlib
import os
import re


class _Config:
    def __init__(self) -> None:
        self.hide_secret = True
        self.secret_patterns = [
            re.compile(r"[A-Za-z0-9]{32,1024}")
        ]
        self.hide_environ = True
        self._environ_values: set[str] = set()
        self.environ_filter = lambda env: len(env) > 8

    @property
    def hide_secret(self) -> bool:
        return self._hide_secret

    @hide_secret.setter
    def hide_secret(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("hide_secret must be a boolean value.")
        self._hide_secret = value

    @property
    def secret_patterns(self) -> list[re.Pattern]:
        return self._secret_patterns

    @secret_patterns.setter
    def secret_patterns(self, patterns: list[re.Pattern]) -> None:
        self._secret_patterns = patterns[:]

    @property
    def hide_environ(self) -> bool:
        return self._hide_environ

    @hide_environ.setter
    def hide_environ(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("hide_secret must be a boolean value.")
        self._hide_environ = value

    @contextlib.contextmanager
    def dump_context(self):
        self._environ_values = set(env for env in os.environ.values() if self.environ_filter(env))
        yield
        self._environ_values = set()


config = _Config()
