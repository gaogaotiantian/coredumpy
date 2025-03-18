# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import os
import re

from .base import TestBase


class TestConfig(TestBase):
    def test_config_object(self):
        from coredumpy import config
        from coredumpy.config import _Config
        self.assertIsInstance(config, _Config)

    def test_hide_secret(self):
        from coredumpy import config
        self.assertTrue(config.hide_secret)

        # this looks like an API key
        secret = "1234ABCD" * 8
        redacted = self.convert_object(secret)
        self.assertNotEqual(redacted, secret)

        with self.assertRaises(ValueError):
            config.hide_secret = 3

        config.hide_secret = False
        non_redacted = self.convert_object(secret)
        self.assertEqual(non_redacted, secret)

        config.hide_secret = True
        pattern = re.compile(r"test")
        config.secret_patterns.append(pattern)
        redacted = self.convert_object("test")
        self.assertNotEqual(redacted, "test")
        config.secret_patterns.remove(pattern)

    def test_hide_environ(self):
        from coredumpy import config
        self.assertTrue(config.hide_environ)

        all_environs = [val for val in os.environ.values() if len(val) > 8]
        env = all_environs[0]
        redacted = self.convert_object(env)
        self.assertNotEqual(redacted, env)

        config.hide_environ = False
        non_redacted = self.convert_object(env)
        self.assertEqual(non_redacted, env)
        config.hide_environ = True

        config.environ_filter = lambda env: False
        non_redacted = self.convert_object(env)
        self.assertEqual(non_redacted, env)
