# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import os


if os.getenv('GITHUB_ACTIONS'):
    try:
        import coredumpy
        coredumpy.patch_unittest(directory=os.getenv('COREDUMPY_DUMP_DIR', './dump'))
    except ImportError:
        pass
