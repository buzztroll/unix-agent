import collections
import unittest

import dcm.agent.docker.list_image as list_image

class TestDockerPlugins(unittest.TestCase):

    def setUp(self):
        """
        :return: a list of the files in src/dcm/agent/jobs/builtin
        """
        FakeConf = collections.namedtuple(
            "FakeConf", ["docker_base_url", "docker_version", "docker_timeout"])
        self.conf = FakeConf('unix://var/run/docker.sock', "1.0.1", 60)

    def tearDown(self):
        pass

    def test_files(self):
        arguments = {}
        list_image.ListImages(self.conf, "400", {}, "test", arguments)
