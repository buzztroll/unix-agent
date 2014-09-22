import collections
import os
import unittest
from nose.plugins import skip
import uuid

import dcmdocker.list_images as list_images
import dcmdocker.import_image as import_image
import dcmdocker.delete_image as delete_image
import dcmdocker.list_containers as list_containers

class TestDockerImageCommands(unittest.TestCase):

    def setUp(self):
        """
        :return: a list of the files in src/dcm/agent/jobs/builtin
        """
        FakeConf = collections.namedtuple(
            "FakeConf", ["docker_base_url", "docker_version", "docker_timeout"])
        self.conf = FakeConf('unix://var/run/docker.sock', "1.0.1", 60)

    def tearDown(self):
        pass

    def test_empty_image_list(self):
        arguments = {}
        plugin = list_images.ListImages(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()

    def test_empty_container_list(self):
        arguments = {}
        plugin = list_containers.DockerListContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()

    def test_import_image_list_delete(self):
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
        for image in reply_obj:
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
        for image in reply_obj:
            if image['Id'] == image_id:
                found_image = image
        self.assertIsNone(found_image)
