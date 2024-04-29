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

    def _get_description(self, test, err):
        class_name = f"{test.__class__.__module__}.{test.__class__.__qualname__}"
        return '\n'.join(['=' * 70,
                          f"FAIL: {test._testMethodName} ({class_name})",
                          '-' * 70,
                          self._exc_info_to_string(err, test).strip()])

    _original_addError = unittest.TestResult.addError
    _original_addFailure = unittest.TestResult.addFailure

    def addError(self, test, err):
        tb = err[2]
        while tb.tb_next:
            tb = tb.tb_next
        try:
            filename = dump(tb.tb_frame, description=_get_description(self, test, err),
                            path=path, directory=directory)
            print(f'Your frame stack is dumped, open it with\n'
                  f'coredumpy load {filename}')
        except Exception:  # pragma: no cover
            print("Failed to dump the frame stack.")
        _original_addError(self, test, err)

    def addFailure(self, test, err):
        tb = err[2]
        while tb.tb_next:
            tb = tb.tb_next
        try:
            filename = dump(tb.tb_frame, description=_get_description(self, test, err),
                            path=path, directory=directory)
            print(f'Your frame stack is dumped, open it with\n'
                  f'coredumpy load {filename}')
        except Exception:  # pragma: no cover
            print("Failed to dump the frame stack.")
        _original_addFailure(self, test, err)

    unittest.TestResult.addError = addError  # type: ignore
    unittest.TestResult.addFailure = addFailure  # type: ignore
