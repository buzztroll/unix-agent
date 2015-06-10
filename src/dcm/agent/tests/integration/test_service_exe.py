from distutils.log import warn
import getpass
import json
import os
import shutil
import tempfile
import unittest

import mock
from nose.plugins import skip
import psutil
from dcm.agent import logger

import dcm.agent.cmd.service as dcmagent
import dcm.agent.cmd.configure as configure
import dcm.agent.tests.utils.general as test_utils


class TestProgramOptions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.run_as_user = getpass.getuser()
        test_utils.connect_to_debugger()
        cls.test_base_path = tempfile.mkdtemp()
        cls.test_conf_path = os.path.join(
            cls.test_base_path, "etc", "agent.conf")
        conf_args = ["-c", "Other",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", cls.test_base_path,
                     "-t", os.path.join(cls.test_base_path, "tmp"),
                     "-C", "ws",
                     "-U", cls.run_as_user,
                     "-l", "/tmp/agent_status_test.log"]
        rc = configure.main(conf_args)
        if rc != 0:
            raise Exception("We could not configure the test env")

    @classmethod
    def tearDownClass(cls):
        logger.clear_dcm_logging()
        shutil.rmtree(cls.test_base_path)

    def tearDown(self):
        if os.path.exists("/tmp/agent_info.tar.gz"):
            os.remove("/tmp/agent_info.tar.gz")

    @mock.patch('dcm.agent.messaging.persistence.SQLiteAgentDB')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_simple_status(self, id_platform, sql_obj):
        id_platform.return_value = ("ubuntu", "14.04")
        rc = dcmagent.main(args=["dcm-agent", "status"])
        print(rc)
        self.assertEqual(rc, 1)

    @mock.patch('dcm.agent.utils.identify_platform')
    def test_simple_tar(self, id_platform):
        id_platform.return_value = ("ubuntu", "14.04")
        rc = dcmagent.main(
            args=["dcm-agent", "-c", self.test_conf_path, "--report"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists("/tmp/agent_info.tar.gz"))

    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_effective_cloud_base_report(self, id_platform, guess_effective_cloud_mock):
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        rc = dcmagent.main(
            args=["dcm-agent", "-c", self.test_conf_path, "--report"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists("/tmp/agent_info.tar.gz"))

    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_real_pid_status(self, id_platform, guess_effective_cloud_mock):
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        pid_file = os.path.join(self.test_base_path, "dcm-agent.pid")
        with open(pid_file, "w") as fptr:
            fptr.write(str(os.getpid()))
        try:
            rc = dcmagent.main(
                args=["dcm-agent", "-c", self.test_conf_path, "status"])
            self.assertEqual(rc, 0)
        finally:
            os.remove(pid_file)

    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_bad_pid_status(self, id_platform, guess_effective_cloud_mock):
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        pid_file = os.path.join(self.test_base_path, "dcm-agent.pid")
        with open(pid_file, "w") as fptr:
            fptr.write("notapid")
        try:
            rc = dcmagent.main(
                args=["dcm-agent", "-c", self.test_conf_path, "status"])
            self.assertEqual(rc, 1)
        finally:
            os.remove(pid_file)

    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_bad_pid_status(self, id_platform, guess_effective_cloud_mock):
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        pid_file = os.path.join(self.test_base_path, "dcm-agent.pid")

        pid_val = None
        pid_list = psutil.pids()
        for i in range(10, 2^15):
            if i not in pid_list:
                pid_val = i
                break
        if pid_val is None:
            warn("No free pid found... huh")
            raise skip.SkipTest("No free pid found")

        with open(pid_file, "w") as fptr:
            fptr.write(str(pid_val))
        try:
            rc = dcmagent.main(
                args=["dcm-agent", "-c", self.test_conf_path, "status"])
            self.assertEqual(rc, 1)
        finally:
            os.remove(pid_file)

    @mock.patch('dcm.agent.messaging.persistence.SQLiteAgentDB')
    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_status_db_jobs_request_lookup(
            self, id_platform, guess_effective_cloud_mock, fake_db):

        class FakeRequest(object):
            def __init__(self, doc):
                self.request_doc = json.dumps({'payload': doc})

        class FakeDB(object):
            def get_all_complete(self):
                return [FakeRequest({'command': 'initialize'})]
            def get_all_reply(self):
                return []
            def get_all_rejected(self):
                return []
            def get_all_ack(self):
                return []
            def get_all_reply_nacked(self):
                return []

        fake_db.return_value = FakeDB()
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        rc = dcmagent.main(
            args=["dcm-agent", "-c", self.test_conf_path, "status"])
        self.assertEqual(rc, 1)

    @mock.patch('dcm.agent.messaging.persistence.SQLiteAgentDB')
    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_status_exception_in_request_lookup(
            self, id_platform, guess_effective_cloud_mock, fake_db):

        class FakeRequest(object):
            def __init__(self, doc):
                self.request_doc = json.dumps({'payload': doc})

        class FakeDB(object):
            def get_all_complete(self):
                return [FakeRequest({'nocommand': 'initialize'})]
            def get_all_reply(self):
                return []
            def get_all_rejected(self):
                return []
            def get_all_ack(self):
                return []
            def get_all_reply_nacked(self):
                return []

        fake_db.return_value = FakeDB()
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        rc = dcmagent.main(
            args=["dcm-agent", "-c", self.test_conf_path, "status"])
        self.assertEqual(rc, 1)

    @mock.patch('dcm.agent.messaging.persistence.SQLiteAgentDB')
    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_status_db_jobs_request_lookup_not_initialized(
            self, id_platform, guess_effective_cloud_mock, fake_db):

        class FakeRequest(object):
            def __init__(self, doc):
                self.request_doc = json.dumps({'payload': doc})

        class FakeDB(object):
            def get_all_complete(self):
                return []
            def get_all_reply(self):
                return [FakeRequest({'command': 'initialize'})]
            def get_all_rejected(self):
                return []
            def get_all_ack(self):
                return []
            def get_all_reply_nacked(self):
                return []

        fake_db.return_value = FakeDB()
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        rc = dcmagent.main(
            args=["dcm-agent", "-c", self.test_conf_path, "status"])
        self.assertEqual(rc, 1)

    @mock.patch('dcm.agent.messaging.persistence.SQLiteAgentDB')
    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_status_db_jobs_request_lookup_rejected_initialized(
            self, id_platform, guess_effective_cloud_mock, fake_db):

        class FakeRequest(object):
            def __init__(self, doc):
                self.request_doc = json.dumps({'payload': doc})

        class FakeDB(object):
            def get_all_complete(self):
                return []
            def get_all_reply(self):
                return []
            def get_all_rejected(self):
                return [FakeRequest({'command': 'initialize'})]
            def get_all_ack(self):
                return []
            def get_all_reply_nacked(self):
                return []

        fake_db.return_value = FakeDB()
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        rc = dcmagent.main(
            args=["dcm-agent", "-c", self.test_conf_path, "status"])
        self.assertEqual(rc, 1)

    @mock.patch('dcm.agent.messaging.persistence.SQLiteAgentDB')
    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_status_db_jobs_request_lookup_acked_initialized(
            self, id_platform, guess_effective_cloud_mock, fake_db):

        class FakeRequest(object):
            def __init__(self, doc):
                self.request_doc = json.dumps({'payload': doc})

        class FakeDB(object):
            def get_all_complete(self):
                return []
            def get_all_reply(self):
                return []
            def get_all_rejected(self):
                return []
            def get_all_ack(self):
                return [FakeRequest({'command': 'initialize'})]
            def get_all_reply_nacked(self):
                return []

        fake_db.return_value = FakeDB()
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        rc = dcmagent.main(
            args=["dcm-agent", "-c", self.test_conf_path, "status"])
        self.assertEqual(rc, 1)

    @mock.patch('dcm.agent.messaging.persistence.SQLiteAgentDB')
    @mock.patch('dcm.agent.cloudmetadata.guess_effective_cloud')
    @mock.patch('dcm.agent.utils.identify_platform')
    def test_status_db_jobs_request_lookup_nacked_initialized(
            self, id_platform, guess_effective_cloud_mock, fake_db):

        class FakeRequest(object):
            def __init__(self, doc):
                self.request_doc = json.dumps({'payload': doc})

        class FakeDB(object):
            def get_all_complete(self):
                return []
            def get_all_reply(self):
                return []
            def get_all_rejected(self):
                return []
            def get_all_ack(self):
                return []
            def get_all_reply_nacked(self):
                return [FakeRequest({'command': 'initialize'})]

        fake_db.return_value = FakeDB()
        id_platform.return_value = ("ubuntu", "14.04")
        guess_effective_cloud_mock.return_value = "Other"
        rc = dcmagent.main(
            args=["dcm-agent", "-c", self.test_conf_path, "status"])
        self.assertEqual(rc, 1)
