import unittest
import dcm.agent.cmd.gen_docs as gen_docs
from types import DictType, ModuleType


class TestGenDocs(unittest.TestCase):


    def setUp(self):
        """
        :return: a list of the files in src/dcm/agent/jobs/builtin
        """
        self.files = gen_docs.filelist


    def tearDown(self):
        self.files = None


    def test_files(self):
        """
        :return: assert that list does not contain .pyc files
                 and that it does contain add_user.py
        """
        assert("__init__.py" not in self.files)
        assert("__init__.pyc" not in self.files)
        assert("add_user.py" in self.files)
        assert("add_user.pyc" not in self.files)


    def test_dynamic_import(self):
        """
        :return: call dynamic_import and assert that it returns a module
        """
        for file in self.files:
            x = gen_docs.dynamic_import(file)
            # it is a module
            assert(isinstance(x, ModuleType))


    def test_get_protocol_argument_dict(self):
        """
        :return: call get_protocol_argument_dict and assert
                 that it returns a dict
        """
        for file in self.files:
            x = gen_docs.dynamic_import(file)
            y = gen_docs.get_protocol_argument_dict(x)
            # it is a dict
            assert(isinstance(y, DictType))


    def test_gen_md_output(self):
        """
        :return: assertion that expected_output is the
                 same as z when remove_user.py is ran through
                 gen_docs.py
        """

        file = 'remove_user.py'

        expected_output = """## remove_user.py parameters:
- userId: The unix account name of the user to remove
    - optional: True
    - type: <type 'str'>
"""

        x = gen_docs.dynamic_import(file)
        y = gen_docs.get_protocol_argument_dict(x)
        z = gen_docs.output_markdown(file,y)

        assert(z == expected_output)

