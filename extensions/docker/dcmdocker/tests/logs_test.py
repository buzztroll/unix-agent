import collections
import os
import unittest
import uuid

from nose.plugins import skip

import dcmdocker.stop_container as stop_container
import dcmdocker.import_image as import_image
import dcmdocker.delete_image as delete_image
import dcmdocker.get_logs_in_container as get_logs_in_container
import dcmdocker.create_container as create_container
import dcmdocker.start_container as start_container
import dcmdocker.delete_container as delete_container
import dcm.agent.plugins.api.pages as pages


class TestDockerContainerLogs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        docker_url = 'http+unix://var/run/docker.sock'
        if 'DOCKER_HOST' in os.environ:
            docker_url = os.environ['DOCKER_HOST']

        def parse_fake(opt_list):
            pass
        FakeConf = collections.namedtuple(
            "FakeConf", ["docker_base_url",
                         "docker_version",
                         "docker_timeout",
                         "parse_config_files",
                         "page_monitor"])
        cls.conf = FakeConf(docker_url, "1.12", 60, parse_fake,
                            pages.PageMonitor())

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

    def test_create_start_log_stop_delete_container(self):
        arguments = {
            "image": self.image_id,
            "command": "/bin/cat /etc/group"}
        plugin = create_container.DockerCreateContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        reply_obj = reply['reply_object']
        container_id = reply_obj['Id']

        print("Container ID " + container_id)
        arguments = {
            "container": container_id
        }
        plugin = start_container.StartContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()

        plugin = get_logs_in_container.GetLogContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        print("top")
        print(str(reply))

        plugin = stop_container.StopContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
        arguments = {
            "container": container_id
        }
        plugin = delete_container.DeleteContainer(
            self.conf, "400", {}, "test", arguments)
        reply = plugin.run()
