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
import os
import subprocess

import dcm.agent.plugins.api.base as plugin_base
from dcm.agent.plugins.api.exceptions import AgentPluginConfigException
import dcm.agent.plugins.loader as plugin_loader


# This plugin directly forks out a script and passes in the arguments it
# received.  This is only used for testing.
class ExePlugin(plugin_base.Plugin):

    def __init__(self, conf, request_id, items_map, name, arguments):
        super(ExePlugin, self).__init__(
            conf, request_id, items_map, name, arguments)
        if 'path' not in items_map:
            raise AgentPluginConfigException(
                "The configuration for the %s plugin does not have "
                "an path entry." % name)
        exe_path = items_map['path']
        if not os.path.exists(exe_path):
            raise AgentPluginConfigException(
                "Module %s is misconfigured.  The path %s "
                "does not exists" % (name, exe_path))
        self.exe = os.path.abspath(exe_path)
        self.cwd = os.path.dirname(self.exe)

    def run(self):
        try:
            return self._exec()
        except Exception as ex:
            self.logger.error("Error running the subprocess", ex)

    def _exec(self):
        args = [self.exe]
        args.extend(self.arguments)
        self.logger.info("Forking the command " + str(args))
        args = ' '.join(args)  # for some reason i cannot just pass the array
                               # at least should do a shell join
        process = subprocess.Popen(args,
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   cwd=self.cwd)

        # TODO iterate over the output so that it does not all come just at
        # the end
        stdout, stderr = process.communicate()
        if stdout is not None:
            stdout = stdout.decode()
        else:
            stdout = ""
        if stderr is not None:
            stderr = stderr.decode()
        else:
            stderr = ""

        self.logger.info("STDOUT: " + stdout)
        self.logger.info("STDERR: " + stderr)
        self.logger.info("Return code: " + str(process.returncode))
        return plugin_base.PluginReply(
            process.returncode, message=stdout, error_message=stderr)

    def cancel(self, *args, **kwargs):
        pass


def _load_exe(conf, request_id, items_map, name, arguments):
    return ExePlugin(conf, request_id, items_map, name, arguments)


def register_test_loader():
    plugin_loader.register_plugin_loader("exe", _load_exe)
