# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import os
import runpy


def startup_conf():
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, "conf_coredumpy.py")):
        runpy.run_path(os.path.join(cwd, "conf_coredumpy.py"))
