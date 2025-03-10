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
import sys
import tokenize
import textwrap
import types
import warnings
from types import CodeType
from typing import Callable, Optional, Union

from .patch import patch_all
from .py_object_container import PyObjectContainer
from .utils import get_dump_filename


class _ExecutableTarget:
    filename: str
    code: Union[CodeType, str]
    namespace: dict


class _ScriptTarget(_ExecutableTarget):
    def __init__(self, target):
        self._target = os.path.realpath(target)

        if not os.path.exists(self._target):
            print(f'Error: {target} does not exist')
            sys.exit(1)
        if os.path.isdir(self._target):
            print(f'Error: {target} is a directory')
            sys.exit(1)

        # If safe_path(-P) is not set, sys.path[0] is the directory
        # of coredumpy, and we should replace it with the directory of the script
        if not getattr(sys.flags, "safe_path", None):
            sys.path[0] = os.path.dirname(self._target)

    @property
    def filename(self):
        return self._target

    @property
    def code(self):
        # Open the file each time because the file may be modified
        import io
        with io.open_code(self._target) as fp:
            return f"exec(compile({fp.read()!r}, {self._target!r}, 'exec'))"

    @property
    def namespace(self):
        return dict(
            __name__='__main__',
            __file__=self._target,
            __builtins__=__builtins__,
            __spec__=None,
        )


class _ModuleTarget(_ExecutableTarget):
    def __init__(self, target):
        self._target = target

        import runpy
        try:
            sys.path.insert(0, os.getcwd())
            _, self._spec, self._code = runpy._get_module_details(self._target)
        except ImportError as e:
            print(f"ImportError: {e}")
            sys.exit(1)
        except Exception:  # pragma: no cover
            import traceback
            traceback.print_exc()
            sys.exit(1)

    @property
    def filename(self):
        return self._code.co_filename

    @property
    def code(self):
        return self._code

    @property
    def namespace(self):
        return dict(
            __name__='__main__',
            __file__=os.path.normcase(os.path.abspath(self.filename)),
            __package__=self._spec.parent,
            __loader__=self._spec.loader,
            __spec__=self._spec,
            __builtins__=__builtins__,
        )


class Coredumpy:
    @classmethod
    def dump(cls,
             frame: Optional[types.FrameType] = None,
             *,
             description: Optional[str] = None,
             depth: Optional[int] = None,
             path: Optional[Union[str, Callable[[], str]]] = None,
             directory: Optional[str] = None):
        """
        dump the current frame stack to a file

        @param frame:
            The top frame to dump, if not specified, the frame of the caller will be used
        @param description:
            The description of the dump, it will be saved in the dump file
        @param depth:
            The depth of the object search
        @param path:
            The path to save the dump file. It could be a string or a callable that returns a string.
            if not specified, the default filename will be used
        @param directory:
            The directory to save the dump file, only works when path is not specified.
        @return:
            The path of the dump file
        """
        if frame is None:
            inner_frame = inspect.currentframe()
            assert inner_frame is not None
            frame = inner_frame.f_back

        output_file = get_dump_filename(frame, path, directory)

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        if output_file.endswith(".json"):
            file_open = open
        else:
            file_open = gzip.open  # type: ignore

        with file_open(output_file, "wt") as f:
            f.write(cls.dumps(frame, description=description, depth=depth))

        return output_file

    @classmethod
    def dumps(cls,
              frame: Optional[types.FrameType] = None,
              *,
              description: Optional[str] = None,
              depth: Optional[int] = None) -> str:
        """
        dump the current frame stack to a string
        @param frame:
            The top frame to dump, if not specified, the frame of the caller will be used
        @param description:
            The description of the dump, it will be saved in the dump file
        @param depth:
            The depth of the object search
        @return:
            The string of the dump
        """
        files = set()
        if frame is None:
            inner_frame = inspect.currentframe()
            assert inner_frame is not None
            frame = inner_frame.f_back

        container = PyObjectContainer()

        frame_id = str(id(frame))

        # The intuitive minimum depth is 1, but we start the count from the
        # frame, which needs frame->f_locals to access the local variables
        # pdb also needs frame->f_code->co_filename to access the source code
        # So we need to add 2 to the depth
        if depth is not None:
            depth = depth + 2

        while frame:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                container.add_object(frame, depth)
            filename = frame.f_code.co_filename
            if filename not in files:
                files.add(filename)
            frame = frame.f_back

        file_lines = {}

        for filename in files:
            if os.path.exists(filename):
                with tokenize.open(filename) as f:
                    file_lines[filename] = f.readlines()

        ret = json.dumps({
            "objects": container.get_objects(),
            "frame": frame_id,
            "files": file_lines,
            "description": description,
            "metadata": cls.get_metadata()
        })

        container.clear()

        return ret

    @classmethod
    def load_data_from_path(cls, path: str):
        if path.endswith(".json"):
            file_open = open
        else:
            file_open = gzip.open  # type: ignore

        with file_open(path, "rt") as f:
            data = json.load(f)

        from coredumpy import __version__
        if data["metadata"]["version"] != __version__:  # pragma: no cover
            print(f"Warning! the dump file is created by {data['metadata']['version']}\n"
                  f"but the current coredumpy version is {__version__}")

        patch_all()

        container = PyObjectContainer()
        container.load_objects(data["objects"])
        frame = container.get_object(data["frame"])

        return container, frame, data["files"]

    @classmethod
    def load(cls, path: str):
        container, frame, files = cls.load_data_from_path(path)
        for filename, lines in files.items():
            linecache.cache[filename] = (len(lines), None, lines, filename)

        pdb_instance = pdb.Pdb()
        pdb_instance.reset()
        pdb_instance.interaction(frame, None)
        container.clear()  # pragma: no cover

    @classmethod
    def peek(cls, path: str):
        if path.endswith(".json"):
            file_open = open
        else:
            file_open = gzip.open  # type: ignore

        with file_open(path, "rt") as f:
            data = json.load(f)

        from coredumpy import __version__
        if data["metadata"]["version"] != __version__:  # pragma: no cover
            print(f"Warning! the dump file is created by {data['metadata']['version']}\n"
                  f"but the current coredumpy version is {__version__}")
        patch_all()
        metadata = data["metadata"]
        system = metadata["system"]
        print(f"{os.path.abspath(path)}")
        print(f"    Python v{metadata['python_version']} on {system['system']} {system['node']} {system['release']}")
        print(f"    {metadata['dump_time']}")
        if data["description"]:
            print(textwrap.indent(data["description"], "    "))

    @classmethod
    def run(cls, options):
        if options.module:
            file = options.module
            target = _ModuleTarget(file)
        else:
            if not options.args:
                print("Error: no script specified")
                sys.exit(1)
            file = options.args.pop(0)
            target = _ScriptTarget(file)

        sys.argv[:] = [file] + options.args

        import __main__
        __main__.__dict__.clear()
        __main__.__dict__.update(target.namespace)

        cmd = target.code

        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")

        from .except_hook import patch_except
        patch_except(path=options.path, directory=options.directory)

        from .unittest_hook import patch_unittest
        patch_unittest(path=options.path, directory=options.directory)

        exec(cmd, __main__.__dict__, __main__.__dict__)

    @classmethod
    def host(cls):
        from .dap_server import run_server
        run_server()

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
dumps = Coredumpy.dumps
load = Coredumpy.load
load_data_from_path = Coredumpy.load_data_from_path
peek = Coredumpy.peek
run = Coredumpy.run
host = Coredumpy.host
