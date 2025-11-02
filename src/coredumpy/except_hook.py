# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import sys
import traceback
from typing import Callable, Optional, Union, Iterable, Type

from .coredumpy import dump


_original_excepthook = sys.excepthook


def patch_except(path: Optional[Union[str, Callable[[], str]]] = None,
                 directory: Optional[str] = None,
                 exclude: Optional[Iterable[Type[BaseException]]] = None):
    """ Patch the excepthook to dump the frame stack when an unhandled exception occurs.

        @param path:
            The path to save the dump file. It could be a string or a callable that returns a string.
            if not specified, the default filename will be used
        @param directory:
            The directory to save the dump file, only works when path is not specified.
        @param exclude:
            A list of exception types to exclude from dumping. If an exception is in this list,
            it will not be dumped and the original excepthook will be called instead.
    """
    if exclude is not None:
        _exclude = tuple(exclude)
        if any(not issubclass(excCls, BaseException) for excCls in _exclude):
            raise TypeError('Expect `exclude` to be BaseException subclasses.')
    else:
        _exclude = tuple()

    def _get_description(type, value, tb):
        side_count = (70 - len(type.__qualname__) - 2) // 2
        headline = f"{'=' * side_count} {type.__qualname__} {'=' * side_count}"
        return '\n'.join([headline,
                          ''.join(traceback.format_exception(type, value, tb)).strip()])

    def _excepthook(type, value, tb):
        if isinstance(value, _exclude):
            _original_excepthook(type, value, tb)
            return

        while tb.tb_next:
            tb = tb.tb_next

        filename = dump(tb.tb_frame, description=_get_description(type, value, tb),
                        path=path, directory=directory)
        _original_excepthook(type, value, tb)
        print(f'Your frame stack is dumped, open it with\n'
              f'coredumpy load {filename}')

    sys.excepthook = _excepthook
