#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
