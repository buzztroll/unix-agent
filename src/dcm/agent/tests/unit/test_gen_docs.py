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
from types import ModuleType
import unittest

import dcm.agent.cmd.gen_docs as gen_docs


class TestGenDocs(unittest.TestCase):

    def setUp(self):
        """
        :return: a list of the files in src/dcm/agent/plugins/builtin
        """
        self.files = gen_docs.filelist

    def tearDown(self):
        self.files = None

    def test_files(self):
        """
        :return: assert that list does not contain .pyc files
                 and that it does contain add_user.py
        """
        assert ("__init__.py" not in self.files)
        assert ("__init__.pyc" not in self.files)
        assert ("add_user.py" in self.files)
        assert ("add_user.pyc" not in self.files)

    def test_dynamic_import(self):
        """
        :return: call dynamic_import and assert that it returns a module
        """
        for file in self.files:
            x = gen_docs.dynamic_import(file)
            # it is a module
            assert (isinstance(x, ModuleType))

    def test_get_protocol_argument_dict(self):
        """
        :return: call get_protocol_argument_dict and assert
                 that it returns a dict
        """
        for file in self.files:
            x = gen_docs.dynamic_import(file)
            y = gen_docs.get_protocol_argument_dict(x)
            # it is a dict
            assert (isinstance(y, dict))

    def test_gen_md_output(self):
        """
        :return: assertion that expected_output is legit
                 when remove_user.py and add_user.py are
                 run through gen_docs.py
        """

        fileone = 'remove_user.py'
        expected_output_fileone = """## remove_user.py parameters:
- userId: The unix account name of the user to remove
    - optional: True
    - type: str
    - default: None
"""

        filetwo = 'add_user.py'
        expected_output_filetwo = """## add_user.py parameters:
- administrator: A string that is either 'true' or 'false' which indicates if the new user should have ssh access
    - optional: True
    - type: str
    - default: None
- authentication: The user's ssh public key
    - optional: True
    - type: str
    - default: None
- firstName: The user's first name
    - optional: True
    - type: str
    - default: None
- lastName: The user's last name
    - optional: True
    - type: str
    - default: None
- userId: The new unix account name to be created
    - optional: True
    - type: Safe user name
    - default: None
"""

        # check remove_user.py
        x = gen_docs.dynamic_import(fileone)
        y = gen_docs.get_protocol_argument_dict(x)
        z = gen_docs.output_markdown(fileone, y)

        assert (z == expected_output_fileone)

        # check add_user.py
        a = gen_docs.dynamic_import(filetwo)
        b = gen_docs.get_protocol_argument_dict(a)
        c = gen_docs.output_markdown(filetwo, b)

        assert (c == expected_output_filetwo)