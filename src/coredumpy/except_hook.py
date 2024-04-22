# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import sys
from typing import Callable, Optional, Union

from .coredumpy import dump


_original_excepthook = sys.excepthook


def patch_except(path: Optional[Union[str, Callable[[], str]]] = None,
                 directory: Optional[str] = None):
    """ Patch the excepthook to dump the frame stack when an unhandled exception occurs.

        @param path:
            The path to save the dump file. It could be a string or a callable that returns a string.
            if not specified, the default filename will be used
        @param directory:
            The directory to save the dump file, only works when path is not specified.
    """

    def _excepthook(type, value, traceback):
        while traceback.tb_next:
            traceback = traceback.tb_next

        filename = dump(traceback.tb_frame, path=path, directory=directory)
        _original_excepthook(type, value, traceback)
        print(f'Your frame stack has been dumped to "{filename}", '
              f'open it with\ncoredumpy load {filename}')

    sys.excepthook = _excepthook
