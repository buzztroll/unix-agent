import os
import tempfile
import unittest
from dcm.agent import utils


class TestProtocolCommands(unittest.TestCase):

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
            file_list = utils.get_config_files(base_dir=tmp_d, conffile=path)
            self.assertIn(path, file_list)
            self.assertIn(path2, file_list)
        finally:
            utils.safe_delete(path)
            utils.safe_delete(path2)
            os.rmdir(tmp_d)
