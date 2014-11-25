import os
import tempfile
import unittest

import dcm.agent
from dcm.agent import handshake
import dcm.agent.config as config


class TestHandshake(unittest.TestCase):

    def setUp(self):
        self.tmp_d = tempfile.mkdtemp()
        root_dir = dcm.agent.get_root_location()

        pluggin_path = os.path.join(root_dir, "etc", "plugin.conf")

        test_conf = """
[workers]
count=1

[connection]
type=ws

[plugin]
configfile=%s

[features]
hello=world
test=2
                """ % pluggin_path

        self.conf_path = os.path.join(self.tmp_d, "agent.conf")
        with open(self.conf_path, "w") as fptr:
            fptr.write(test_conf)

    def tearDown(self):
        try:
            os.removedirs(self.tmp_d)
        except:
            pass

    def test_get_conf_files(self):
        conf = config.AgentConfig([self.conf_path])
        handshake_doc = handshake.get_handshake(conf)
        features = handshake_doc['features']
        self.assertIsNotNone(features['plugins'])
        self.assertIn("add_user", features['plugins'])
        self.assertIn("hello", features)
        self.assertIn("test", features)
        self.assertEqual(features["hello"], "world")
        self.assertEqual(features["test"], '2')
