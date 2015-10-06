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
import unittest
import uuid

import dcmdocker.pull_repo as pull_repo
import dcmdocker.list_images as list_images
import dcmdocker.import_image as import_image
import dcmdocker.delete_image as delete_image
import dcmdocker.list_containers as list_containers
import dcmdocker.tests.utils as test_utils


class TestDockerImageCommands(unittest.TestCase):

    def setUp(self):
        """
        :return: a list of the files in src/dcm/agent/plugins/builtin
        """
        self.conf = test_utils.get_docker_conf_obj()

    def tearDown(self):
        pass

    def test_pull_repo(self):
        arguments = {'repository': 'ubuntu'}
        plugin = pull_repo.PullRepo(
            self.conf, "400", {}, "test", arguments)
        plugin.run()

    def test_empty_image_list(self):
        arguments = {}
        plugin = list_images.ListImages(
            self.conf, "400", {}, "test", arguments)
        plugin.run()

    def test_empty_container_list(self):
        arguments = {}
        plugin = list_containers.DockerListContainer(
            self.conf, "400", {}, "test", arguments)
        plugin.run()

    def test_import_image_list_delete(self):
        if 'DCM_DOCKER_IMAGE_LOCATION' not in os.environ:
            raise unittest.SkipTest('skipping')

        image_location = os.environ['DCM_DOCKER_IMAGE_LOCATION']

        repo = "agenttest" + str(uuid.uuid4()).split("-")[0]
        arguments = {
            "src": image_location,
            "repository": repo,
            "tag": "1.0"
        }
        plugin = import_image.ImportImage(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        reply_obj = reply['reply_object']
        image_id = reply_obj['status']

        arguments = {}
        plugin = list_images.ListImages(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        reply_obj = reply['reply_object']

        found_image = None
        for image in reply_obj['images']:
            if image['Id'] == image_id:
                found_image = image
        self.assertIsNotNone(found_image)

        arguments = {"name": image_id}
        plugin = delete_image.DeleteImages(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        reply_obj = reply['reply_object']

        arguments = {}
        plugin = list_images.ListImages(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        reply_obj = reply['reply_object']
        found_image = None
        for image in reply_obj['images']:
            if image['Id'] == image_id:
                found_image = image
        self.assertIsNone(found_image)
