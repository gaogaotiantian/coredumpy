# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import os
import sys

from .coredumpy import dump


_original_excepthook = sys.excepthook


def _excepthook(type, value, traceback):
    while traceback.tb_next:
        traceback = traceback.tb_next

    filename = os.path.abspath("coredumpy_dump")
    dump(filename, traceback.tb_frame)
    _original_excepthook(type, value, traceback)
    print(f'Your frame stack has been dumped to "{filename}", '
          f'open it with\ncoredumpy load {filename}')


def patch_excepthook():
    sys.excepthook = _excepthook
