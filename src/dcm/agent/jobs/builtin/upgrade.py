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
import json
import logging
import os
import urllib2

import dcm.agent
from dcm.agent import config
import dcm.agent.jobs as jobs
import dcm.agent.utils as utils


_g_logger = logging.getLogger(__name__)


class Upgrade(jobs.Plugin):

    protocol_arguments = {
        "newVersion": ("The version of the agent to upgrade to.",
                       True, str, None),
        "url": ("The location of the script to be run to handle the upgrade",
                True, str, None),
        "args": ("The list of arguments to be passed to the upgrade script",
                 True, list, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(Upgrade, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        response = urllib2.urlopen(self.args.url)
        data = response.read()

        script_file = self.conf.get_temp_file("upgradescript")
        opts_file = self.conf.get_temp_file("upgradeopts")
        try:
            with open(script_file, "w") as f:
                f.write(data)
            os.chmod(script_file, 0x755)

            # write the configuration to a file.  We may not be safe assuming
            # that the default configuration location is correct
            opts_list = config.build_options_list()
            opts_dict = {}
            for opt in opts_list:
                if opt.section not in opts_dict:
                    opts_dict[opt.section] = {}
                opts_dict[opt.section][opt.name] = getattr(
                    self.conf, opt.get_option_name())

            with open(opts_file, "w") as f:
                for section_name in opts_dict:
                    f.write("[" + section_name + "]" + os.linesep)
                    section = opts_dict[section_name]
                    for key in section:
                        f.write("%s=%s" % (key, section[key]))
                        f.write(os.linesep)

            command_list = [script_file,
                            self.args.newVersion,
                            dcm.agent.g_version,
                            opts_file]
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
            if os.path.exists(opts_file):
                utils.secure_delete(self.conf, opts_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return Upgrade(conf, job_id, items_map, name, arguments)
