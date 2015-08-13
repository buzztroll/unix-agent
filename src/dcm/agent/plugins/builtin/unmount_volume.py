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
import dcm.agent.exceptions as exceptions
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.utils as plugin_utils
import dcm.agent.utils as utils


def _unmount(conf, mount_point):
    command = [conf.get_script_location("unmount"), mount_point]
    (stdout, stderr, rc) = plugin_utils.run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)
    return rc


def close_encrypted_device(conf, encrypted_device_id):
    command = [conf.get_script_location("closeEncryption"),
               encrypted_device_id]
    (stdout, stderr, rc) = plugin_utils.run_command(conf, command)
    if rc != 0:
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)
    return rc


class UnmountVolume(plugin_base.Plugin):

    protocol_arguments = {
        "deviceId": ("The mount point ID to unmount.", True, str, None),
        "encrypted": ("If using an encrypted device this is the "
                      "device id to remove.", False, bool, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(UnmountVolume, self).__init__(
            conf, job_id, items_map, name, arguments)

    def umount(self):
        device_mappings = utils.get_device_mappings(self.conf)

        for mapping in device_mappings:
            d_id = mapping["device_id"]
            mount_point = mapping["mount_point"]
            if d_id == self.args.deviceId:
                _unmount(self.conf, mount_point)
                break

    def run(self):
        try:
            self.umount()
            if self.args.encrypted:
                plugin_utils.close_encrypted_device(
                    self.conf, self.args.deviceId)
            return plugin_base.PluginReply(0, reply_type="void")
        except exceptions.AgentExecutableException as aex:
            return plugin_base.PluginReply(1, reply_type="void",
                                           error_message=str(aex))


def load_plugin(conf, job_id, items_map, name, arguments):
    return UnmountVolume(conf, job_id, items_map, name, arguments)
