# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import argparse
import os
import runpy

from .coredumpy import load, peek, run, host


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    subparsers_run = subparsers.add_parser("run", help="Run a file/module with coredumpy enabled.")
    subparsers_run.add_argument("-m", metavar="module", dest="module")
    subparsers_run.add_argument("--path", help="The path of dump file", default=None)
    subparsers_run.add_argument("--directory", help="The directory of dump file", default=None)
    subparsers_run.add_argument("--conf", help="The startup configuration file to run", default=None)

    subparsers_load = subparsers.add_parser("load", help="Load a dump file.")
    subparsers_load.add_argument("file", type=str, help="The dump file to load.")
    subparsers_load.add_argument("--ipdb", action="store_true", help="Use ipdb as the debugger.")
    subparsers_load.add_argument("--conf", help="The startup configuration file to run", default=None)

    subparsers_peek = subparsers.add_parser("peek", help="Peek a dump file.")
    subparsers_peek.add_argument("files", help="The dump file to load.", nargs="+")

    subparsers_host = subparsers.add_parser("host", help="Host a DAP server.")
    subparsers_host.add_argument("--conf", help="The startup configuration file to run", default=None)

    options, args = parser.parse_known_args()

    if hasattr(options, "conf") and options.conf and os.path.exists(options.conf):
        runpy.run_path(options.conf)

    if options.command == "load":
        if os.path.exists(options.file):
            debugger = "ipdb" if options.ipdb else "pdb"
            load(options.file, debugger=debugger)
        else:
            print(f"File {options.file} not found.")
    elif options.command == "peek":
        for file in options.files:
            if os.path.exists(file):
                if os.path.isdir(file):
                    for f in os.listdir(file):
                        try:
                            path = os.path.join(file, f)
                            peek(path)
                        except Exception:
                            pass
                else:
                    try:
                        peek(file)
                    except Exception:
                        pass
            else:
                print(f"File {file} not found.")
    elif options.command == "run":
        run(options, args)
    elif options.command == "host":
        host()
