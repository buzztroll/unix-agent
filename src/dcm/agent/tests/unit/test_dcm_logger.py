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
from distutils.log import warn
import getpass
import logging
import os
import tempfile
import unittest
import urllib.parse
import uuid
import mock

import dcm.agent
import dcm.agent.config as config
import dcm.agent.logger as logger
from dcm.agent.events.globals import global_space as dcm_events


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
        log_file_str = log_file_str.replace("@DCM_USER@", getpass.getuser())
        log_file_str = log_file_str.replace(
            "@LOGFILE_PATH@", cls.base_log_file)

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

    def test_remote_logger_callback(self):
        conn = mock.Mock()
        token = "xyz123"
        msg = "short message ::"
        level = "debug"
        logger.send_log_to_dcm_callback(
            conn=conn, token=token, message=msg, level=level)
        args, kwargs = conn.send.call_args
        log_dict = args[0]
        self.assertEqual(log_dict['type'], "LOG")
        self.assertEqual(log_dict['token'], token)
        self.assertEqual(log_dict['level'], level)
        self.assertNotIn(':', log_dict['message'])
        self.assertEqual(urllib.parse.unquote(log_dict['message']), msg)

    def test_logging_handler_without_conn(self):
        logger_name = str(uuid.uuid4())
        my_logger = logging.getLogger(logger_name)
        handler = logger.dcmLogger()
        my_logger.addHandler(handler)
        my_logger.error("Test message")

    def test_logging_handler_with_conn(self):
        conn = mock.Mock()
        conf = mock.Mock()
        logger_name = str(uuid.uuid4())
        my_logger = logging.getLogger(logger_name)
        handler = logger.dcmLogger()
        my_logger.addHandler(handler)
        logger.set_dcm_connection(conf, conn)
        msg = "Test message with conn"
        my_logger.error(msg)
        handler.flush()
        dcm_events.poll(timeblock=0.0)
        args, kwargs = conn.send.call_args
        log_dict = args[0]
        self.assertEqual(log_dict['type'], "LOG")
        self.assertEqual(log_dict['level'], "ERROR")
        self.assertEqual(urllib.parse.unquote(log_dict['message']), msg)
