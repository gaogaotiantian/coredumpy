# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import unittest
from typing import Callable, Optional, Union

from .coredumpy import dump


def patch_unittest(path: Optional[Union[str, Callable[[], str]]] = None,
                   directory: Optional[str] = None):
    """ Patch unittest to coredump when a test fails/raises an exception.

        @param path:
            The path to save the dump file. It could be a string or a callable that returns a string.
            if not specified, the default filename will be used
        @param directory:
            The directory to save the dump file, only works when path is not specified.
    """

    _original_addError = unittest.TestResult.addError
    _original_addFailure = unittest.TestResult.addFailure

    def addError(self, test, err):
        tb = err[2]
        while tb.tb_next:
            tb = tb.tb_next
        try:
            filename = dump(tb.tb_frame, path=path, directory=directory)
            print(f'Your frame stack has been dumped to "{filename}", '
                  f'open it with\ncoredumpy load {filename}')
        except Exception:  # pragma: no cover
            pass
        _original_addError(self, test, err)

    def addFailure(self, test, err):
        tb = err[2]
        while tb.tb_next:
            tb = tb.tb_next
        try:
            filename = dump(tb.tb_frame, path=path, directory=directory)
            print(f'Your frame stack has been dumped to "{filename}", '
                  f'open it with\ncoredumpy load {filename}')
        except Exception:  # pragma: no cover
            pass
        _original_addFailure(self, test, err)

    unittest.TestResult.addError = addError  # type: ignore
    unittest.TestResult.addFailure = addFailure  # type: ignore
