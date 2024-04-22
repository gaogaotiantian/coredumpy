# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import os


def normalize_commands(commands):
    if os.getenv("COVERAGE_RUN"):
        if commands[0] == "python":
            commands = ["coverage", "run", "--parallel-mode"] + commands[1:]
        elif commands[0] == "coredumpy":
            commands = ["coverage", "run", "--parallel-mode", "-m", "coredumpy"] + commands[1:]
    return commands
