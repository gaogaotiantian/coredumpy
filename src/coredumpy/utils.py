# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import datetime
import os


def get_dump_filename(frame, path, directory):
    if path is not None:
        if directory is not None:
            raise ValueError("Cannot specify both path and directory")
        if callable(path):
            return os.path.abspath(path())
        return os.path.abspath(path)

    funcname = os.path.basename(frame.f_code.co_name)
    d = datetime.datetime.now()
    filename = f"coredumpy_{funcname}_{d.strftime('%Y%m%d_%H%M%S_%f')}.dump"

    if directory is None:
        return os.path.abspath(filename)

    return os.path.abspath(os.path.join(directory, filename))
