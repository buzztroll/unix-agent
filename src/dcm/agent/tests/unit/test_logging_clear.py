from distutils.log import warn
import getpass
import logging
import os
import shutil
import tempfile
import unittest

import mock
from nose.plugins import skip
import psutil
from dcm.agent import logger, config

import dcm.agent
import dcm.agent.cmd.configure as configure
import dcm.agent.tests.utils.general as test_utils


class TestLoggingClear(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        root_dir = dcm.agent.get_root_location()
        src_logging_path = os.path.join(root_dir, "etc", "logging.yaml")
        _, cls.base_log_file = tempfile.mkstemp()
        _, cls.log_conf_file = tempfile.mkstemp()

        with open(src_logging_path, "r") as fptr:
            log_file_str = fptr.read()

        log_file_str = log_file_str.replace("@LOG_LEVEL@", "DEBUG")
        log_file_str = log_file_str.replace("@LOGFILE_PATH@", cls.base_log_file)

        with open(cls.log_conf_file, "w") as fptr:
            fptr.write(log_file_str)
        config.setup_logging(cls.log_conf_file)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.base_log_file)
        os.remove(cls.log_conf_file)

    def setUp(self):
        self._logger = logging.getLogger(__name__)

    def test_basic_log_clear(self):
        self._logger.info("TEST LOG LINE")
        start_size = os.stat(self.base_log_file).st_size
        self.assertGreater(start_size, 0)
        logger.delete_logs()
        end_size = os.stat(self.base_log_file).st_size
        self.assertEqual(end_size, 0)
        # then keep logging
        self._logger.info("MORE TEST LOG LINES")
        final_size = os.stat(self.base_log_file).st_size
        self.assertGreater(final_size, 0)
