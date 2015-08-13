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
import logging

import dcm.agent.plugins.api.base as plugin_base
from dcm.agent.plugins.builtin.add_user import AddUser
from dcm.agent.plugins.builtin.rename import Rename
import dcm.agent.plugins.api.utils as plugin_utils
import dcm.agent.utils as agent_utils


_g_logger = logging.getLogger(__name__)


class InitializeJob(plugin_base.Plugin):

    protocol_arguments = {
        "cloudId":
        ("The cloud ID on which this agent is running.",
         True, str, None),
        "customerId":
        ("The ID of the customer running this server.  A new user will be "
         "created with the name c<customerId>.",
         True, int, None),
        "regionId":
        ("Sets the default region that will be used by this agent in "
         "future cloud related operations",
         True, str, None),
        "zoneId":
        ("The default zone that will be used by this agent in future "
         "cloud operations.", True, str, None),
        "serverId":
        ("A unique ID for this server.  This will be used in future "
         "communication with the agent manager as a means of "
         "authentication.",
         True, str, None),
        "serverName":
        ("The name of this server. The hostname will be set to this value.",
         True, str, None),
        "encryptedEphemeralFsKey":
        ("The file system key for encrypted ephemeral file systems.",
         True, plugin_utils.base64type_convertor, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InitializeJob, self).__init__(
            conf, job_id, items_map, name, arguments)

        self.rename = Rename(self.conf, self.job_id, {"script_name": "rename"},
                             "rename",
                             {"serverName": self.arguments["serverName"]})
        self.add_user = AddUser(self.conf, self.job_id,
                                {"script_name": "addUser"}, "add_user",
                                {"firstName": "Customer",
                                 "lastName": "Account",
                                 "password": None,
                                 "authentication": None,
                                 "administrator": "false",
                                 "userId": agent_utils.make_id_string(
                                     "c", self.args.customerId)})

    def run(self):
        _g_logger.debug("Initialize run")
        # verify that the parameters in initialize match what came in on the
        # connection
        try:
            plugin_utils.log_to_dcm_console_job_details(
                job_name=self.name,
                details="Renaming the host to %s" % self.args.serverName)
            res_obj = self.rename.run()
            if res_obj.get_return_code() != 0:
                res_obj.set_message(res_obj.get_message() + " : rename failed")
                return res_obj

            # add customer user
            plugin_utils.log_to_dcm_console_job_details(
                job_name=self.name, details="Adding the user")
            res_obj = self.add_user.run()
            if res_obj.get_return_code() != 0:
                res_obj.set_message(res_obj.get_message() + " : addUser failed")
                return res_obj

            self.conf.state = "RUNNING"
            return plugin_base.PluginReply(0, reply_type="void")
        except Exception as ex:
            _g_logger.exception("initialize failed: " + str(ex))
            return plugin_base.PluginReply(1, message=str(ex))


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return InitializeJob(conf, job_id, items_map, name, arguments)
