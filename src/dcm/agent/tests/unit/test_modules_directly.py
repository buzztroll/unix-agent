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
from collections import namedtuple
import unittest

import dcm.agent.plugins.loader as plugin_loader

class TestHandshake(unittest.TestCase):

    def test_mount_volume_supported(self):
        FakeConf = namedtuple('FakeConf', 'cloud_type platform_name')
        conf = FakeConf('Amazon', 'ubuntu')
        module = 'dcm.agent.plugins.builtin.mount_volume'
        items_map = {'type': 'python_module',
                     'module_name': module}
        features = plugin_loader.get_module_features(
            conf, 'mount_volume', items_map)
        self.assertIn('mount', features)
        self.assertIn('format', features)

    def test_mount_volume_unsupported_cloud(self):
        FakeConf = namedtuple('FakeConf', 'cloud_type platform_name')
        conf = FakeConf('NotACloud', 'ubuntu')
        module = 'dcm.agent.plugins.builtin.mount_volume'
        items_map = {'type': 'python_module',
                     'module_name': module}
        features = plugin_loader.get_module_features(
            conf, 'mount_volume', items_map)
        self.assertFalse(features)

    def test_mount_volume_unsupported_platform(self):
        FakeConf = namedtuple('FakeConf', 'cloud_type platform_name')
        conf = FakeConf('Amazon', 'NotReal')
        module = 'dcm.agent.plugins.builtin.mount_volume'
        items_map = {'type': 'python_module',
                     'module_name': module}
        features = plugin_loader.get_module_features(
            conf, 'mount_volume', items_map)
        self.assertFalse(features)

    def test_mount_volume_unsupported_everything(self):
        FakeConf = namedtuple('FakeConf', 'cloud_type platform_name')
        conf = FakeConf('NotACloud', 'NotReal')
        module = 'dcm.agent.plugins.builtin.mount_volume'
        items_map = {'type': 'python_module',
                     'module_name': module}
        features = plugin_loader.get_module_features(
            conf, 'mount_volume', items_map)
        self.assertFalse(features)
