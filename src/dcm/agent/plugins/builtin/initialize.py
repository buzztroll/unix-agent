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
            res_doc = self.rename.run()
            if res_doc["return_code"] != 0:
                res_doc["message"] = res_doc["message"] + " : rename failed"
                return res_doc

            # add customer user
            plugin_utils.log_to_dcm_console_job_details(
                job_name=self.name, details="Adding the user")
            res_doc = self.add_user.run()
            if res_doc["return_code"] != 0:
                res_doc["message"] = res_doc["message"] + " : addUser failed"
                return res_doc

            self.conf.state = "RUNNING"
            return {"return_code": 0, "message": "",
                    "error_message": "", "reply_type": "void"}
        except Exception as ex:
            _g_logger.exception("initialize failed: " + str(ex))
            return {'return_code': 1, "message": str(ex)}


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return InitializeJob(conf, job_id, items_map, name, arguments)
