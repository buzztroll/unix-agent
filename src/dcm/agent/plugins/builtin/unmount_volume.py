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
import logging
import os
import stat

_g_logger = logging.getLogger(__name__)


def _is_block_device(device_id):
    try:
        mode = os.stat("/dev/" + device_id).st_mode
    except FileNotFoundError:
        mode = 0
    return stat.S_ISBLK(mode)


def _translate_ubuntu_device_id(device_id):
    if not _is_block_device(device_id) and device_id.startswith("sd"):
        _g_logger.info("Returning %s" % device_id.replace("sd", "xvd"))
        return device_id.replace("sd", "xvd")
    _g_logger.info("Returning %s" % device_id)
    return device_id

_device_translate_map = {
    "ubuntu": _translate_ubuntu_device_id
}


def _unmount(conf, mount_point):
    command = [conf.get_script_location("unmount"), mount_point]
    (stdout, stderr, rc) = plugin_utils.run_command(conf, command)
    if rc != 0:
        _g_logger.info("The unmount of %s did not succeed: %s" % (mount_point, stderr))
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)
    return rc


def _close_encrypted_device(conf, encrypted_device_id):
    command = [conf.get_script_location("closeEncryption"),
               encrypted_device_id]
    (stdout, stderr, rc) = plugin_utils.run_command(conf, command)
    if rc != 0:
        _g_logger.info("The close of encrypted %s did not succeed: %s" % (encrypted_device_id, stderr))
        raise exceptions.AgentExecutableException(command, rc, stdout, stderr)
    return rc


def _check_for_device_translations(platform, device_id):
    _g_logger.info("Checking for device translations")
    try:
        device_id = _device_translate_map[platform](device_id)
    except KeyError:
        raise Exception("Unmount is not supported on %s" % platform)
    return device_id


def _find_device_to_unmount(conf, device_id, platform, device_mappings):
    translated_device = _check_for_device_translations(platform, device_id)
    for mapping in device_mappings:
        d_id = mapping["device_id"]
        mount_point = mapping["mount_point"]
        encrypted = mapping["encrypted"]
        if d_id == translated_device:
            return d_id, mount_point, encrypted
    return False, "No such volume %s" % translated_device, False


def _check_if_device_encrypted(device_id, device_mappings):
    for dev_map in device_mappings:
        if dev_map["encrypted"] and device_id in dev_map["device_id"]:
            return "es" + device_id
    return device_id


class UnmountVolume(plugin_base.Plugin):

    protocol_arguments = {
        "deviceId": ("The mount point ID to unmount.", True, str, None),
        "encrypted": ("If using an encrypted device this is the "
                      "device id to remove.", False, bool, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(UnmountVolume, self).__init__(
            conf, job_id, items_map, name, arguments)

    def unmount(self, mount_point):
        _g_logger.info("Found a match in device mappings for %s...attempting unmount" % mount_point)
        _unmount(self.conf, mount_point)

    def run(self):
        device_mappings = utils.get_device_mappings(self.conf)
        platform = self.conf.platform_name
        try:
            device_id = _check_if_device_encrypted(self.args.deviceId, device_mappings)
            (d_id, mount_point, encrypted) = _find_device_to_unmount(self.conf,
                                                                     device_id,
                                                                     platform,
                                                                     device_mappings)
            if "No such volume" in mount_point:
                return plugin_base.PluginReply(1, reply_type="void",
                                               error_message=mount_point)
            self.unmount(mount_point)
            if encrypted:
                _g_logger.info("Attempting to close encrypted device %s" % d_id)
                _close_encrypted_device(
                    self.conf, d_id)
            return plugin_base.PluginReply(0, reply_type="void")
        except exceptions.AgentExecutableException as aex:
            return plugin_base.PluginReply(1, reply_type="void",
                                           error_message=str(aex))


def load_plugin(conf, job_id, items_map, name, arguments):
    return UnmountVolume(conf, job_id, items_map, name, arguments)
