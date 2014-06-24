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

import dcm.agent.jobs as jobs
import dcm.agent.utils as utils


_g_logger = logging.getLogger(__name__)


class RunScript(jobs.Plugin):

    protocol_arguments = {
        "b64script": ("A base64 encoded executable.", True,
                      utils.base64type_convertor),
        "checksum": ("The checksum of the script.", True, str),
        "arguments": ("The list of arguments to be passed to the script",
                      True, list)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RunScript, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):

        script_file = self.conf.get_temp_file("exe_script")
        try:
            with open(script_file, "w") as f:
                f.write(self.args.b64script)
            os.chmod(script_file, 0x755)

            command_list = [script_file]
            command_list.extend(self.args.args)
            _g_logger.debug("Plugin running the command %s"
                            % str(command_list))
            (stdout, stderr, rc) = utils.run_command(self.conf, command_list)
            _g_logger.debug("Command %s: stdout %s.  stderr: %s" %
                            (str(command_list), stdout, stderr))
            reply = {"return_code": rc, "message": stdout,
                     "error_message": stderr, "return_type": "void"}
            return reply
        finally:
            if os.path.exists(script_file):
                utils.secure_delete(self.conf, script_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return RunScript(conf, job_id, items_map, name, arguments)
