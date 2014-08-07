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
import dcm.agent.utils as utils
import dcm.agent.exceptions as exceptions
import dcm.agent.jobs as jobs

_g_logger = logging.getLogger(__name__)


class DirectPass(jobs.Plugin):
    """
    This plugin can be used for those scripts that need no massaging.  We
    simply take the remote arguments and look up the command and run it.
    All that subclasses need to do is set the ordered list of parameters
    for the script.
    """

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DirectPass, self).__init__(
            conf, job_id, items_map, name, arguments)
        self.ordered_param_list = []
        self.cwd = None

        try:
            script_name = items_map["script_name"]
            self.exe_path = conf.get_script_location(script_name)

            utils.log_to_dcm(logging.DEBUG,
                             "script name: %s, exe: %s"
                             % (script_name, self.exe_path))
            if not os.path.exists(self.exe_path):
                raise exceptions.AgentPluginConfigException(
                    "The plugin %s points an add_user_exe_path that does not "
                    "exist." % name)
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, ke.message))

    def run(self):
        command_list = [self.exe_path]
        command_list.extend(self.ordered_param_list)
        _g_logger.debug("Plugin running the command %s" % str(command_list))

        (stdout, stderr, rc) = utils.run_command(
            self.conf, command_list, cwd=self.cwd)
        _g_logger.debug("Command %s: stdout %s.  stderr: %s" %
                        (str(command_list), stdout, stderr))
        reply = {"return_code": rc, "message": stdout,
                 "error_message": stderr, "return_type": "void"}
        return reply


def load_plugin(conf, job_id, items_map, name, arguments):
    return DirectPass(conf, job_id, items_map, name, arguments)
