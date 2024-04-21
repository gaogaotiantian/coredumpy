# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import inspect
import json
import linecache
import tokenize
import pdb

from .patch import patch_all
from .py_object_proxy import PyObjectProxy


class Coredumpy:
    @classmethod
    def dump(cls, path, frame=None):
        files = set()
        if frame is None:
            frame = inspect.currentframe().f_back
        curr_frame = frame
        while frame:
            filename = frame.f_code.co_filename

            if filename not in files:
                files.add(filename)

            PyObjectProxy.add_object(frame)
            frame = frame.f_back

        with open(path, "w") as f:
            json.dump({
                "objects": PyObjectProxy._objects,
                "frame": str(id(curr_frame)),
                "files": {filename: tokenize.open(filename).readlines() for filename in files}
            }, f)

    @classmethod
    def load(cls, path):
        with open(path, "r") as f:
            data = json.load(f)
        patch_all()
        for filename, lines in data["files"].items():
            linecache.cache[filename] = (len(lines), None, lines, filename)

        PyObjectProxy.load_objects(data["objects"])
        frame = PyObjectProxy.load_object(data["frame"])
        pdb_instance = pdb.Pdb()
        pdb_instance.reset()
        pdb_instance.interaction(frame, None)


dump = Coredumpy.dump
load = Coredumpy.load
