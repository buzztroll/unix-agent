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
from dcm.agent import exceptions

import dcm.agent.utils as utils
import dcm.agent.jobs as jobs


class StartService(jobs.Plugin):

    protocol_arguments = {
        "customerId":
            ("The ID of the customer envoking the command.", True, str),
        "serviceId":
            ("The ID of the service to start.", True, str)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(StartService, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name),
                        arguments["serviceId"]]
        self.cwd = self.conf.get_service_directory(arguments["serviceId"])

    def run(self):
        (stdout, stderr, rc) = utils.run_command(
            self.conf, self.command, cwd=self.cwd)
        # NOTE(buzztroll) this is a little bit different than the other
        # reply docs.  here we let a non 0 rc through to tell enstratius
        # what happened to the status.  I am not sure that i like this
        # but it keeps parity with the previous agent
        reply_doc = {
            "return_code": 0,
            "reply_type": "int",
            "reply_object": rc
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return StartService(conf, job_id, items_map, name, arguments)
