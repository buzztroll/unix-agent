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
from dcm.agent import exceptions
import dcm.agent.utils as utils
import dcm.agent.jobs.direct_pass as direct_pass


class AddUser(direct_pass.DirectPass):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(AddUser, self).__init__(
            conf, job_id, items_map, name, arguments)

        try:
            self._ordered_param_list = [conf.customer_id,
                                        arguments["user_id"],
                                        arguments["first_name"],
                                        arguments["last_name"],
                                        arguments["administrator"],
                                        arguments["password"]]
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, ke.message))

        if 'password' not in arguments['password'] or not arguments['password']:
            self.arguments["password"] = utils.generate_password()

    def run(self):
        key_file = self.agent.get_temp_file(self.user_id + ".pub")

        try:
            with open(key_file, "w") as f:
                f.write(self.ssh_public_key)
            return super(AddUser, self).call()
        finally:
            os.remove(key_file)

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return AddUser(conf, job_id, items_map, name, arguments)
