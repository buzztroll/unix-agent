import os
import tempfile
import unittest

import mock

import dcm.agent
import dcm.agent.config as config
import dcm.agent.handshake as handshake


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

[storage]
base_dir=%s

[features]
hello=world
test=2
                """ % (pluggin_path, self.tmp_d)

        os.mkdir(os.path.join(self.tmp_d, "secure"))

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
        hs = handshake.HandshakeManager(conf, mock.Mock())
        handshake_doc = hs.get_send_document()
        features = handshake_doc['features']
        self.assertIsNotNone(features['plugins'])
        self.assertIn("add_user", features['plugins'])
        self.assertIn("hello", features)
        self.assertIn("test", features)
        self.assertEqual(features["hello"], "world")
        self.assertEqual(features["test"], '2')
