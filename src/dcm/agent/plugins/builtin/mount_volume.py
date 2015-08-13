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

from dcm.agent.cloudmetadata import CLOUD_TYPES
import dcm.agent.config as config
import dcm.agent.exceptions as exceptions
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.exceptions as plugin_exceptions
import dcm.agent.plugins.api.utils as plugin_utils
import dcm.agent.utils as utils


_cloud_stack_map = {
    "1": "xvdb",
    "2": "xvdc",
    "4": "xvde",
    "5": "xvdf",
    "6": "xvdg",
    "7": "xvdh",
    "8": "xvdi",
    "9": "xvdj"
}

_support_matrix = {
    CLOUD_TYPES.Amazon.lower(): [config.PLATFORM_TYPES.PLATFORM_UBUNTU.lower()]
}

_g_logger = logging.getLogger(__name__)

_g_platform_dep_installer = {
    config.PLATFORM_TYPES.PLATFORM_UBUNTU: ["debInstall",
                                            "--no-install-recommends",
                                            "mdadm"],
}

_g_platform_dep_crypto_installer = {
    config.PLATFORM_TYPES.PLATFORM_UBUNTU: ["debInstall",
                                            "cryptsetup"],
}


def _is_supported(conf):
    try:
        supported_distros = _support_matrix[conf.cloud_type.lower()]
    except KeyError:
        return False
    return conf.platform_name.lower() in supported_distros


class MountVolume(plugin_base.ScriptPlugin):

    protocol_arguments = {
        "formatVolume":
        ("A boolean indicating if the volume should be formatted.",
         True, bool, None),
        "fileSystem":
        ("The file system type to which the volume will be formatted",
         True, str, None),
        "raidLevel": ("The RAID configuration to use", True, str, "NONE"),
        "encryptedFsEncryptionKey":
        ("The encryption key for encrypted volumes", False,
         plugin_utils.base64type_binary_convertor, None),
        "mountPoint": ("The directory on which the volume will be mounted",
                       False, str, None),
        "devices": ("The list of devices that will be used.",
                    True, list, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(MountVolume, self).__init__(
            conf, job_id, items_map, name, arguments)

    def _install_deps(self, dep_dict):
        if self.conf.platform_name in dep_dict:
            _g_logger.debug("Installing packaging deps")
            pkg_installer_cmd = \
                dep_dict[self.conf.platform_name]
            if pkg_installer_cmd:
                cmd_path = self.conf.get_script_location(pkg_installer_cmd[0])
                pkg_installer_cmd[0] = cmd_path
                (stdout, stderr, rc) = plugin_utils.run_command(
                    self.conf, pkg_installer_cmd)
                _g_logger.debug("Results of install: stdout: %s, stderr: "
                                "%s, rc %d" % (str(stdout), str(stderr), rc))

    def setup_encryption(self, device_id, encrypted_device_id, key_file_path):
        command = [self.conf.get_script_location("setupEncryption"),
                   device_id,
                   encrypted_device_id,
                   key_file_path]
        (stdout, stderr, rc) = plugin_utils.run_command(self.conf, command)
        if rc != 0:
            raise exceptions.AgentExecutableException(
                command, rc, stdout, stderr)
        return rc

    def write_key_file(self, block_device):
        if self.args.encryptedFsEncryptionKey is None:
            return None

        if block_device:
            key_file_dir = self.conf.storage_temppath
        else:
            key_file_dir = os.path.join(self.conf.storage_base_dir, "tmp")
        key_file_path = os.path.join(key_file_dir, "fskey.txt")

        with open(key_file_path, "wb") as fptr:
            fptr.write(self.args.encryptedFsEncryptionKey)

        return key_file_path

    def format(self, device_id):
        return utils.agent_format(
            self.conf, device_id, self.args.fileSystem,
            self.args.mountPoint, self.args.encryptedFsEncryptionKey)

    def configure_raid(self, device_id):
        _g_logger.info("Configuring RAID on " + str(device_id))
        if self.args.formatVolume:
            exe = self.conf.get_script_location("configureRaid")
        else:
            exe = self.conf.get_script_location("assembleRaid")

        if self.args.raidLevel.upper() == "NONE":
            raise plugin_exceptions.AgentPluginParameterBadValueException(
                "mount_volume",
                "raidLevel",
                "When using multiple volumes you must specify a RAID level")

        try:
            raid_level = str(int(self.args.raidLevel[4:]))
        except:
            raise plugin_exceptions.AgentPluginParameterBadValueException(
                "mount_volume",
                "raidLevel",
                "Invalid RAID level")

        cmd = [exe, raid_level, device_id]

        for d in self.args.devices:
            cmd.append(d)

        _g_logger.debug("Running the raid configuration command %s" % str(cmd))
        (stdout, stderr, rc) = plugin_utils.run_command(self.conf, cmd)
        _g_logger.debug("configure raid results: %d stdout=%s stderr=%s" %
                        (rc, str(stdout), str(stderr)))

        if rc != 0:
            _g_logger.error(
                "Failed to run raid configuration: stdout=%s\nstderr=%s"
                % (str(stdout), str(stderr)))
            raise exceptions.AgentExecutableException(
                cmd, rc, stdout, stderr)

    def _normalize_device(self):
        if self.conf.cloud_type != CLOUD_TYPES.CloudStack and\
                self.conf.cloud_type != CLOUD_TYPES.CloudStack3:
            return self.args.devices[:]
        modified_device_list = []
        for target_device in self.args.devices:
            if target_device not in _cloud_stack_map:
                raise plugin_exceptions.AgentPluginParameterBadValueException(
                    "mount_volume",
                    "raidLevel",
                    "When using cloud stack the device must be one of: %s" %
                    str(list(_cloud_stack_map.keys())))
            modified_device_list.append(_cloud_stack_map[target_device])
        return modified_device_list

    def mount_block_volume(self):
        if not self.args.devices:
            return 0

        if len(self.args.devices) > 1 and\
                self.args.raidLevel.upper() == "NONE":
            raise plugin_exceptions.AgentPluginException(
                "Must specify a RAID volume with mounting multiple devices at "
                "once.")

        if len(self.args.devices) > 1:
            target_device = "md0"
        else:
            target_device = self.args.devices[0]

        _g_logger.debug("target device is " + target_device)

        td = target_device
        if self.args.encryptedFsEncryptionKey is not None:
            encrypted_device = "es" + target_device
            td = encrypted_device
            self._install_deps(_g_platform_dep_crypto_installer)

        device_mappings = utils.get_device_mappings(self.conf)
        for mapping in device_mappings:
            if mapping["device_id"] == td:
                return 0

        if len(self.args.devices) > 1:
            self.configure_raid(target_device)

        if self.args.formatVolume:
            if self.args.encryptedFsEncryptionKey:
                key_file_path = None
                try:
                    key_file_path = self.write_key_file(True)
                    self.setup_encryption(
                        target_device, encrypted_device, key_file_path)
                    utils.open_encrypted_device(self.conf,
                                                target_device,
                                                encrypted_device,
                                                key_file_path)
                    target_device = encrypted_device
                finally:
                    if key_file_path:
                        utils.safe_delete(key_file_path)
            self.format(target_device)
        elif self.args.encryptedFsEncryptionKey:
            key_file_path = None
            try:
                key_file_path = self.write_key_file(True)
                utils.open_encrypted_device(self.conf,
                                            target_device,
                                            encrypted_device,
                                            key_file_path)
                target_device = encrypted_device
            finally:
                plugin_utils.safe_delete(key_file_path)
        utils.mount(self.conf,
                    target_device,
                    self.args.fileSystem,
                    self.args.mountPoint)
        return 0

    def run(self):
        if not _is_supported(self.conf):
            raise exceptions.AgentUnsupportedCloudFeature(
                "mount is not supported on the distro " +
                self.conf.cloud_type.lower() + " and cloud " +
                self.conf.platform_name.lower())

        if self.args.mountPoint is None:
            self.args.mountPoint = self.conf.storage_mountpoint

        # if the mount point exists and is not empty we cannot use it
        if os.path.exists(self.args.mountPoint):
            if os.listdir(self.args.mountPoint):
                raise exceptions.AgentOptionException(
                    "The path %s exists.  For safety the agent only mounts "
                    "volumes on paths that do not exist or are empty.")

        if self.args.fileSystem is None:
            self.args.fileSystem = self.conf.storage_default_file_system

        self.args.devices = self._normalize_device()
        self._install_deps(_g_platform_dep_installer)
        rc = self.mount_block_volume()

        return plugin_base.PluginReply(rc, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return MountVolume(conf, job_id, items_map, name, arguments)


def get_features(conf):
    if _is_supported(conf):
        return {'mount': True,
                'format': True}
    return {}
