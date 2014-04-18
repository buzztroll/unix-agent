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
import dcm.agent.exceptions as exceptions
import dcm.agent.jobs as jobs
import dcm.agent.utils as utils


class UnmountVolume(jobs.Plugin):

    protocol_arguments = {
        "deviceId":
            ("The device ID to unmount.", True, str),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(UnmountVolume, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        try:
            utils.unmount(self.args.deviceId)
            return {"return_code": 0, "message": "",
                    "error_message": "", "return_type": "void"}
        except exceptions.AgentExecutableException as aex:
            return {"return_code": 1, "message": "",
                    "error_message": aex.message, "return_type": "void"}


def load_plugin(conf, job_id, items_map, name, arguments):
    return UnmountVolume(conf, job_id, items_map, name, arguments)
