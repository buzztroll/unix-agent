import logging
import os
import tempfile
import unittest

import dcm.agent.utils as utils
import dcm.agent.cmd.service as service


class TestUtils(unittest.TestCase):

    def test_safe_delete_no_exists(self):
        # test non existent file
        rc = utils.safe_delete("no/such/file")
        self.assertTrue(rc)

    def test_get_conf_files(self):
        tmp_d = tempfile.mkdtemp()
        osf, path = tempfile.mkstemp()
        osf, path2 = tempfile.mkstemp()
        os.environ["DCM_AGENT_CONF"] = path2

        try:
            file_list = service.get_config_files(base_dir=tmp_d, conffile=path)
            self.assertIn(path, file_list)
            self.assertIn(path2, file_list)
        finally:
            utils.safe_delete(path)
            utils.safe_delete(path2)
            os.rmdir(tmp_d)

    def test_stack_trace(self):
        utils.build_assertion_exception(logging, "a message")
