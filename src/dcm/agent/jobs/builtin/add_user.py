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
import logging
import os

import dcm.agent.jobs.direct_pass as direct_pass
import dcm.agent.utils as agent_util


class AddUser(direct_pass.DirectPass):

    protocol_arguments = {
        "userId": ("The new unix account name to be created", True,
                   agent_util.user_name, None),
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
            agent_util.log_to_dcm(
                logging.INFO,
                "Attempting to add the user %s." % self.args.userId)
            rc = super(AddUser, self).run()
            agent_util.log_to_dcm(
                logging.INFO,
                "The user %s was added." % self.args.userId)
            return rc
        finally:
            if os.path.exists(key_file):
                agent_util.secure_delete(self.conf, key_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return AddUser(conf, job_id, items_map, name, arguments)
