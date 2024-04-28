# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import datetime
import gzip
import inspect
import json
import linecache
import os
import pdb
import platform
import tokenize
import types
import warnings
from typing import Callable, Optional, Union

from .patch import patch_all
from .py_object_proxy import PyObjectProxy
from .utils import get_dump_filename


class Coredumpy:
    @classmethod
    def dump(cls,
             frame: Optional[types.FrameType] = None,
             *,
             path: Optional[Union[str, Callable[[], str]]] = None,
             directory: Optional[str] = None):
        """
        dump the current frame stack to a file

        @param frame:
            The top frame to dump, if not specified, the frame of the caller will be used
        @param path:
            The path to save the dump file. It could be a string or a callable that returns a string.
            if not specified, the default filename will be used
        @param directory:
            The directory to save the dump file, only works when path is not specified.
        @return:
            The path of the dump file
        """
        files = set()
        if frame is None:
            inner_frame = inspect.currentframe()
            assert inner_frame is not None
            frame = inner_frame.f_back
        curr_frame = frame
        while frame:
            filename = frame.f_code.co_filename

            if filename not in files:
                files.add(filename)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                PyObjectProxy.add_object(frame)
            frame = frame.f_back

        output_file = get_dump_filename(curr_frame, path, directory)

        file_lines = {}

        for filename in files:
            if os.path.exists(filename):
                with tokenize.open(filename) as f:
                    file_lines[filename] = f.readlines()

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with gzip.open(output_file, "wt") as f:
            json.dump({
                "objects": PyObjectProxy._objects,
                "frame": str(id(curr_frame)),
                "files": file_lines,
                "metadata": cls.get_metadata()
            }, f)

        PyObjectProxy.clear()

        return output_file

    @classmethod
    def load(cls, path):
        with gzip.open(path, "rt") as f:
            data = json.load(f)

        from coredumpy import __version__
        if data["metadata"]["version"] != __version__:  # pragma: no cover
            print(f"Warning! the dump file is created by {data['metadata']['version']}\n"
                  f"but the current coredumpy version is {__version__}")
        patch_all()
        for filename, lines in data["files"].items():
            linecache.cache[filename] = (len(lines), None, lines, filename)

        PyObjectProxy.load_objects(data["objects"])
        frame = PyObjectProxy.load_object(data["frame"])
        pdb_instance = pdb.Pdb()
        pdb_instance.reset()
        pdb_instance.interaction(frame, None)
        PyObjectProxy.clear()  # pragma: no cover

    @classmethod
    def get_metadata(cls):
        from coredumpy import __version__
        uname = platform.uname()
        return {
            "version": __version__,
            "python_version": platform.python_version(),
            "dump_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": {
                "system": uname.system,
                "node": uname.node,
                "release": uname.release,
            }
        }


dump = Coredumpy.dump
load = Coredumpy.load
