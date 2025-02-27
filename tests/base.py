# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt


import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

from coredumpy.py_object_container import PyObjectContainer

from .util import normalize_commands


class TestBase(unittest.TestCase):
    def run_test(self, script, dumppath, commands, use_cli_run=False):
        script = textwrap.dedent(script)
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(f"{tmpdir}/script.py", "w") as f:
                f.write(script)
            if use_cli_run:
                subprocess.run(normalize_commands(["coredumpy", "run", f"{tmpdir}/script.py", "--path", dumppath]),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(normalize_commands([sys.executable, f"{tmpdir}/script.py"]),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            process = subprocess.Popen(normalize_commands(["coredumpy", "load", dumppath]),
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout, stderr = process.communicate("\n".join(commands).encode())
            stdout = stdout.decode(errors='backslashreplace')
            stderr = stderr.decode(errors='backslashreplace')
        try:
            os.remove(dumppath)
        except FileNotFoundError:
            pass
        return stdout, stderr

    def run_script(self, script, expected_returncode=0):
        script = textwrap.dedent(script)
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(f"{tmpdir}/script.py", "w") as f:
                f.write(script)
            process = subprocess.Popen(normalize_commands([sys.executable, f"{tmpdir}/script.py"]),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            stdout = stdout.decode(errors='backslashreplace')
            stderr = stderr.decode(errors='backslashreplace')
            self.assertEqual(process.returncode, expected_returncode,
                             f"script failed with return code {process.returncode}\n{stderr}")
        return stdout, stderr

    def run_run(self, args):
        process = subprocess.Popen(normalize_commands(["coredumpy", "run"] + args),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        stdout = stdout.decode(errors='backslashreplace')
        stderr = stderr.decode(errors='backslashreplace')
        return stdout, stderr

    def run_peek(self, paths):
        process = subprocess.Popen(normalize_commands(["coredumpy", "peek"] + paths),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        stdout = stdout.decode(errors='backslashreplace')
        stderr = stderr.decode(errors='backslashreplace')
        return stdout, stderr

    def convert_object(self, obj):
        container = PyObjectContainer()
        container.add_object(obj)
        container.load_objects(container.get_objects())
        return container.get_object(str(id(obj)))
