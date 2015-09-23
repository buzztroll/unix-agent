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
import logging
import os
import tempfile
import unittest

import dcm.agent.config as config
from dcm.agent.plugins.api.utils import json_param_type
import dcm.agent.utils as utils


class TestUtils(unittest.TestCase):

    def test_safe_delete_no_exists(self):
        # test non existent file
        rc = utils.safe_delete("no/such/file")
        self.assertTrue(rc)

    def test_get_conf_files(self):
        osf, path = tempfile.mkstemp()
        osf, path2 = tempfile.mkstemp()
        os.environ["DCM_AGENT_CONF"] = path2

        try:
            file_list = config.get_config_files(conffile=path)
            self.assertIn(path, file_list)
            self.assertIn(path2, file_list)
        finally:
            utils.safe_delete(path)
            utils.safe_delete(path2)

    def test_stack_trace(self):
        utils.build_assertion_exception(logging, "a message")

    def test_json_params(self):
        res = json_param_type(None)
        self.assertIsNone(res)
        res = json_param_type("null")
        self.assertIsNone(res)
        res = json_param_type('{"x": 1}')
        self.assertTrue('x' in res.keys())
        self.assertEqual(res['x'], 1)
        res = json_param_type({"x": 1})
        self.assertTrue('x' in res.keys())
        self.assertEqual(res['x'], 1)
