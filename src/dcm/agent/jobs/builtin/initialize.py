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
from dcm.agent import utils
from dcm.agent.jobs.builtin.add_user import AddUser
from dcm.agent.jobs.builtin.make_temp import MakeTemp
from dcm.agent.jobs.builtin.rename import Rename

import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class InitializeJob(jobs.Plugin):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InitializeJob, self).__init__(
            conf, job_id, items_map, name, arguments)

        self.rename = Rename(self.conf, self.job_id, {"script_name": "rename"},
                             "rename",
                             {"server_name": self.arguments["serverName"]})
        self.make_temp = MakeTemp(self.conf, self.job_id,
                                  {"script_name": "makeTemp"}, "make_temp",
                                  {})
        self.add_user = AddUser(self.conf, self.job_id,
                                {"script_name": "addUser"}, "add_user",
                                {"first_name": "Customer",
                                 "last_name": "Account",
                                 "password": None,
                                 "authentication": None,
                                 "administrator": "false",
                                 "user_id": utils.make_id_string("c", self.conf.customer_id)})

    def run(self):
        _g_logger.debug("Initialize run")
        # verify that the parameters in initialize match what came in on the
        # connection
        try:
            # TODO WALK THE INIT STEPS
            # rename
            self.logger.info("Renaming the host to %s" % self.arguments["serverName"])
            res_doc = self.rename.run()
            if res_doc["return_code"] != 0:
                res_doc["message"] = res_doc["message"] + " : rename failed"
                return res_doc

            if self.conf.storage_mount_enabled:
                self.logger.debug("Mount is enabled")
                if self.arguments["ephemeralFileSystem"]:
                    self.logger.info("Attempting to mount the ephemeral file system")
                    # TODO mount encrypted FS

            # make the temp directory
            self.logger.info("Create the temporary directory")
            self.make_temp.run()
            if res_doc["return_code"] != 0:
                res_doc["message"] = res_doc["message"] + " : makeTemp failed"
                return res_doc
            # add customer user
            self.logger.info("Adding the user")
            self.add_user.run()
            if res_doc["return_code"] != 0:
                res_doc["message"] = res_doc["message"] + " : addUser failed"
                return res_doc

            return {"return_code": 0, "message": "",
                 "error_message": "", "return_type": "void"}
        except Exception as ex:
            return {'return_code': 1, "message": ex.message}

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return InitializeJob(conf, job_id, items_map, name, arguments)
