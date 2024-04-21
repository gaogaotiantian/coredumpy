# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import argparse
import os

from .coredumpy import load


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    subparsers_load = subparsers.add_parser("load", help="Load a dump file.")
    subparsers_load.add_argument("file", type=str, help="The dump file to load.")

    args = parser.parse_args()

    if args.command == "load":
        if os.path.exists(args.file):
            load(args.file)
        else:
            print(f"File {args.file} not found.")
