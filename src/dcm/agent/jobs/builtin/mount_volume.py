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
from dcm.agent import exceptions
import dcm.agent.utils as utils
import dcm.agent.config as config
import dcm.agent.jobs.direct_pass as direct_pass
from dcm.agent.cloudmetadata import CLOUD_TYPES


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


def _is_supported(conf):
    try:
        supported_distros = _support_matrix[conf.cloud_type.lower()]
    except KeyError:
        return False
    return conf.platform_name.lower() in supported_distros


class MountVolume(direct_pass.DirectPass):

    protocol_arguments = {
        "formatVolume":
        ("A boolean indicating if the volume should be formated.",
         True, bool, None),
        "fileSystem": ("", True, str, None),
        "raidLevel": ("", True, str, "NONE"),
        "encryptedFsEncryptionKey": ("", False,
                                     utils.base64type_binary_convertor, None),
        "mountPoint": ("", True, str, None),
        "devices": ("", True, list, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(MountVolume, self).__init__(
            conf, job_id, items_map, name, arguments)

    def _install_deps(self):
        if self.conf.platform_name in _g_platform_dep_installer:
            _g_logger.debug("Installing packaging deps")
            pkg_installer_cmd = \
                _g_platform_dep_installer[self.conf.platform_name]
            if pkg_installer_cmd:
                cmd_path = self.conf.get_script_location(pkg_installer_cmd[0])
                pkg_installer_cmd[0] = cmd_path
                (stdout, stderr, rc) = utils.run_command(
                    self.conf, pkg_installer_cmd)
                _g_logger.debug("Results of install: stdout: %s, stderr: "
                                "%s, rc %d" % (str(stdout), str(stderr), rc))

    def setup_encryption(self, device_id, encrypted_device_id, key_file_path):
        command = [self.conf.get_script_location("setupEncryption"),
                   device_id,
                   encrypted_device_id,
                   key_file_path]
        (stdout, stderr, rc) = utils.run_command(self.conf, command)
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

        with open(key_file_path, "w") as fptr:
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

        cmd = [exe, device_id]

        for d in self.args.devices:
            cmd.append(d)

        _g_logger.debug("Running the raid configuration command %s" % str(cmd))
        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
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
                raise exceptions.AgentPluginBadParameterException(
                "mount_volume",
                "When using cloud stack the device must be one of: %s" %
                str(_cloud_stack_map.keys()))
            modified_device_list.append(_cloud_stack_map[target_device])
        return modified_device_list

    def mount_block_volume(self):
        if not self.args.devices:
            return 0

        if len(self.args.devices) > 1 and\
                self.args.raidLevel.upper() == "NONE":
            raise exceptions.AgentJobException(
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
                utils.safe_delete(key_file_path)
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

        if self.args.fileSystem is None:
            self.args.fileSystem = self.conf.storage_default_file_system

        self.args.devices = self._normalize_device()
        self._install_deps()
        rc = self.mount_block_volume()

        reply = {"return_code": rc, "message": "",
                 "error_message": "", "reply_type": "void"}
        return reply


def load_plugin(conf, job_id, items_map, name, arguments):
    return MountVolume(conf, job_id, items_map, name, arguments)


def get_features(conf):
    if _is_supported(conf):
        return {'mount': True,
                'format': True}
    return {}
