import collections
import os
import socket
import unittest
import urlparse
from nose.plugins import skip
import uuid

import dcmdocker.import_image as import_image
import dcmdocker.delete_image as delete_image
import dcmdocker.list_containers as list_containers
import dcmdocker.create_container as create_container
import dcmdocker.start_container as start_container
import dcmdocker.stop_container as stop_container
import dcmdocker.delete_container as delete_container
from src.dcm.agent.jobs import pages


class TestDockerContainer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        docker_url = 'http+unix://var/run/docker.sock'
        cls.host = '127.0.0.1'
        if 'DOCKER_HOST' in os.environ:
            docker_url = os.environ['DOCKER_HOST']
            p = urlparse.urlparse(docker_url)
            cls.host = p.hostname

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
        :return: a list of the files in src/dcm/agent/jobs/builtin
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

        print "Container ID " + container_id
        arguments = {
            "container": container_id,
            "port_bindings": {5050: ("0.0.0.0", 5050)}
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
