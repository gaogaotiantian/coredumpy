# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import os
import sys


def normalize_commands(commands):
    if os.getenv("COVERAGE_RUN"):
        if commands[0] == "python" or commands[0] == sys.executable:
            commands = [sys.executable, "-m", "coverage", "run", "--parallel-mode"] + commands[1:]
        elif commands[0] == "coredumpy":
            commands = [sys.executable, "-m", "coverage", "run", "--parallel-mode", "-m", "coredumpy"] + commands[1:]
    return commands
