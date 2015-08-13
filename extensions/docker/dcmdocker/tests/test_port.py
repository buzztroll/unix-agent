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
import collections
import os
import socket
import unittest
import urllib.parse
import uuid

from nose.plugins import skip

import dcmdocker.stop_container as stop_container
import dcmdocker.import_image as import_image
import dcmdocker.delete_image as delete_image
import dcmdocker.list_containers as list_containers
import dcmdocker.create_container as create_container
import dcmdocker.start_container as start_container
import dcmdocker.delete_container as delete_container
import dcmdocker.tests.utils as test_utils


class TestDockerContainer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.conf = test_utils.get_docker_conf_obj()

        if 'DCM_DOCKER_IMAGE_LOCATION' not in os.environ:
            raise skip.SkipTest('skipping')

        image_location = os.environ['DCM_DOCKER_IMAGE_LOCATION']
        repo = "agenttest" + str(uuid.uuid4()).split("-")[0]
        arguments = {
            "src": image_location,
            "repository": repo,
            "tag": "1.0"
        }
        plugin = import_image.ImportImage(
            cls.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        reply_obj = reply['reply_object']
        cls.image_id = reply_obj['status']

    @classmethod
    def tearDownClass(cls):
        arguments = {"name": cls.image_id}
        plugin = delete_image.DeleteImages(
            cls.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        reply_obj = reply['reply_object']

    def setUp(self):
        """
        :return: a list of the files in src/dcm/agent/plugins/builtin
        """
        pass

    def tearDown(self):
        pass

    def test_connect_to_local_port(self):
        msg_str = str(uuid.uuid4())
        arguments = {
            "image": self.image_id,
            "command": "/bin/bash -c '/bin/echo %s | "
                       "/bin/nc -l -p 5050'" % msg_str,
            "ports": [5050]}
        plugin = create_container.DockerCreateContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        reply_obj = reply['reply_object']
        container_id = reply_obj['Id']

        print("Container ID " + container_id)
        arguments = {
            "container": container_id,
            "port_bindings": {5050: [("0.0.0.0", 5050)]}
        }
        plugin = start_container.StartContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()

        arguments = {}
        plugin = list_containers.DockerListContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()

        try:
            sock = socket.create_connection((self.host, 5050))
            received_data = sock.recv(1024).strip()
            self.assertEqual(received_data, msg_str)
        finally:
            arguments = {
                "container": container_id}

            plugin = stop_container.StopContainer(
                self.conf, "400", {}, "test", arguments)
            reply = plugin.run()
            arguments = {
                "container": container_id
            }
            plugin = delete_container.DeleteContainer(
                self.conf, "400", {}, "test", arguments)
            reply = plugin.run()
