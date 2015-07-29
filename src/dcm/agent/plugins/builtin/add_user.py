#  ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================
import os

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

            plugin_utils.log_to_dcm_console_job_details(
                job_name=self.name,
                details="The user %s was added." % self.args.userId)
            return rc
        finally:
            if os.path.exists(key_file):
                plugin_utils.secure_delete(self.conf, key_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return AddUser(conf, job_id, items_map, name, arguments)
