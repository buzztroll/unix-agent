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

import os
from dcm.agent import exceptions
import dcm.agent.utils as utils
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


class MountVolume(direct_pass.DirectPass):

    protocol_arguments = {
        "formatVolume":
        ("A boolean indicating if the volume should be formated.",
         True, bool, None),
        "fileSystem": ("", True, str, None),
        "raidLevel": ("", True, str, None),
        "encryptedFsEncryptionKey": ("", False, utils.base64type_convertor, None),
        "mountPoint": ("", True, str, None),
        "devices": ("", True, list, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(MountVolume, self).__init__(
            conf, job_id, items_map, name, arguments)

        if self.args.raidLevel is None or self.args.raidLevel.upper() != "NONE":
            raise exceptions.AgentPluginBadParameterException(
                "mount_volume", "only raid level NONE is supported.")

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
        if self.args.formatVolume:
            exe = self.conf.get_script_location("configureRaid")
        else:
            exe = self.conf.get_script_location("assembleRaid")

        cmd = [exe, device_id]

        for d in self.args.devices:
            cmd.append(d)

        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
        if rc != 0:
            raise exceptions.AgentExecutableException(
                cmd, rc, stdout, stderr)
        return rc

    def _normalize_device(self):
        if len(self.args.devices) > 1:
            return "md0"
        target_device = self.args.devices[0]
        if self.conf.cloud_type == CLOUD_TYPES.CloudStack or\
            self.conf.cloud_type == CLOUD_TYPES.CloudStack3:
            if target_device not in _cloud_stack_map:
                raise exceptions.AgentPluginBadParameterException(
                "mount_volume",
                "When using cloud stack the device must be one of: %s" %
                str(_cloud_stack_map.keys()))
            return _cloud_stack_map[target_device]
        return _cloud_stack_map

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
        if self.args.mountPoint is None:
            self.args.mountPoint = self.conf.storage_mountpoint

        if self.args.fileSystem is None:
            self.args.fileSystem = self.conf.storage_default_file_system

        rc = self.mount_block_volume()

        reply = {"return_code": rc, "message": "",
                 "error_message": "", "reply_type": "void"}
        return reply


def load_plugin(conf, job_id, items_map, name, arguments):
    return MountVolume(conf, job_id, items_map, name, arguments)
