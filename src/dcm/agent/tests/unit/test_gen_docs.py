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
                 same as z when add_user.py is ran through
                 gen_docs.py
        """

        file = 'add_user.py'

        expected_output = """## add_user.py parameters:
- lastName: The user's last name
    - optional: True
    - type: <type 'str'>
- authentication: The user's ssh public key
    - optional: True
    - type: <type 'str'>
- userId: The new unix account name to be created
    - optional: True
    - type: <type 'str'>
- administrator: A string that is either 'true' or 'false' which indicates if the new user should havessh access
    - optional: True
    - type: <type 'str'>
- firstName: The user's first name
    - optional: True
    - type: <type 'str'>
"""

        x = gen_docs.dynamic_import(file)
        y = gen_docs.get_protocol_argument_dict(x)
        z = gen_docs.output_markdown(file,y)

        assert(z == expected_output)

