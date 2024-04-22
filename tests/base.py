# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import os
import subprocess
import tempfile
import textwrap
import unittest

from .util import normalize_commands


class TestBase(unittest.TestCase):
    def run_test(self, script, dumppath, commands):
        script = textwrap.dedent(script)
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(f"{tmpdir}/script.py", "w") as f:
                f.write(script)
            subprocess.run(normalize_commands(["python", f"{tmpdir}/script.py"]),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            process = subprocess.Popen(normalize_commands(["coredumpy", "load", dumppath]),
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout, stderr = process.communicate("\n".join(commands).encode())
            stdout = stdout.decode()
            stderr = stderr.decode()
        try:
            os.remove(dumppath)
        except FileNotFoundError:
            pass
        return stdout, stderr

    def run_script(self, script):
        script = textwrap.dedent(script)
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(f"{tmpdir}/script.py", "w") as f:
                f.write(script)
            process = subprocess.Popen(normalize_commands(["python", f"{tmpdir}/script.py"]),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            stdout = stdout.decode()
            stderr = stderr.decode()
        return stdout, stderr
