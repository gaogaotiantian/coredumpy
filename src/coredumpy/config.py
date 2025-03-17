# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import re


class _Config:
    def __init__(self) -> None:
        self._hide_secret = True
        self.secret_patterns = [
            re.compile(r"[A-Za-z0-9]{32,1024}")
        ]

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


config = _Config()
