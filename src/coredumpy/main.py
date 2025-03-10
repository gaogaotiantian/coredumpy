# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import argparse
import os

from .coredumpy import load, peek, run, host


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    subparsers_run = subparsers.add_parser("run", help="Run a file/module with coredumpy enabled.")
    subparsers_run.add_argument("-m", metavar="module", dest="module")
    subparsers_run.add_argument("--path", help="The path of dump file", default=None)
    subparsers_run.add_argument("--directory", help="The directory of dump file", default=None)
    subparsers_run.add_argument("args", nargs="*")

    subparsers_load = subparsers.add_parser("load", help="Load a dump file.")
    subparsers_load.add_argument("file", type=str, help="The dump file to load.")

    subparsers_peek = subparsers.add_parser("peek", help="Peek a dump file.")
    subparsers_peek.add_argument("files", help="The dump file to load.", nargs="+")

    subparsers_peek = subparsers.add_parser("host", help="Host a DAP server.")

    args = parser.parse_args()

    if args.command == "load":
        if os.path.exists(args.file):
            load(args.file)
        else:
            print(f"File {args.file} not found.")
    elif args.command == "peek":
        for file in args.files:
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
    elif args.command == "run":
        run(args)
    elif args.command == "host":
        host()
