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
import os

import dcm.agent.messaging.persistence as persistence
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.utils as plugin_utils


class AddUser(plugin_base.ScriptPlugin):

    protocol_arguments = {
        "userId": ("The new unix account name to be created", True,
                   plugin_utils.user_name, None),
        "firstName": ("The user's first name", True, str, None),
        "lastName": ("The user's last name", True, str, None),
        "authentication": ("The user's ssh public key", True, str, None),
        "administrator": ("A string that is either 'true' or 'false' "
                          "which indicates if the new user should have "
                          "ssh access", True, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(AddUser, self).__init__(
            conf, job_id, items_map, name, arguments)

        self.ordered_param_list = [self.args.userId,
                                   self.args.userId,
                                   self.args.firstName,
                                   self.args.lastName,
                                   self.args.administrator.lower()]
        self.ssh_public_key = self.args.authentication
        self._db = persistence.SQLiteAgentDB(conf.storage_dbfile)

    def run(self):
        key_file = self.conf.get_temp_file(self.args.userId + ".pub")

        try:
            if self.ssh_public_key:
                with open(key_file, "w") as f:
                    f.write(self.ssh_public_key)
                self.ordered_param_list.append(key_file)

            plugin_utils.log_to_dcm_console_job_details(
                job_name=self.name,
                details="Attempting to add the user %s." % self.args.userId)

            rc = super(AddUser, self).run()

            admin_bool = self.args.administrator.lower() == "true"
            self._db.add_user(
                self.conf.agent_id, self.args.userId, self.ssh_public_key,
                admin_bool)

            plugin_utils.log_to_dcm_console_job_details(
                job_name=self.name,
                details="The user %s was added." % self.args.userId)
            return rc
        finally:
            if os.path.exists(key_file):
                plugin_utils.secure_delete(self.conf, key_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return AddUser(conf, job_id, items_map, name, arguments)
