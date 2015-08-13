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
import os
import urllib.error
import urllib.parse
import urllib.request

import dcm.agent
import dcm.agent.config as config
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.utils as plugin_utils


_g_logger = logging.getLogger(__name__)


class Upgrade(plugin_base.Plugin):

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
        response = urllib.request.urlopen(self.args.url)
        data = response.read()

        script_file = self.conf.get_temp_file("upgradescript")
        opts_file = self.conf.get_temp_file("upgradeopts")
        try:
            with open(script_file, "wb") as f:
                f.write(data)
            os.chmod(script_file, 0o755)

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
            (stdout, stderr, rc) = plugin_utils.run_command(
                self.conf, command_list)
            _g_logger.debug("Command %s: stdout %s.  stderr: %s" %
                            (str(command_list), stdout, stderr))
            return plugin_base.PluginReply(
                rc, message=stdout, error_message=stderr, reply_type="void")
        finally:
            if os.path.exists(script_file):
                plugin_utils.secure_delete(self.conf, script_file)
            if os.path.exists(opts_file):
                plugin_utils.secure_delete(self.conf, opts_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return Upgrade(conf, job_id, items_map, name, arguments)
