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


class MountVolume(direct_pass.DirectPass):

    protocol_arguments = {
        "userId": ("The new unix account name to be created", True, str),
        "firstName": ("The user's first name", True, str),
        "lastName": ("The user's last name", True, str),
        "authentication": ("The user's ssh public key", True, str),
        "administrator": ("A string that is either 'true' or 'false' "
                          "which indicates if the new user should have"
                          "ssh access", True, str)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(MountVolume, self).__init__(
            conf, job_id, items_map, name, arguments)

        try:
            self.ordered_param_list = [arguments["userId"],
                                       arguments["userId"],
                                       arguments["firstName"],
                                       arguments["lastName"],
                                       arguments["administrator"],
                                       arguments["password"]]
            self.ssh_public_key = arguments["authentication"]
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, ke.message))

        if not arguments['password']:
            self.arguments["password"] = utils.generate_password()

    def mount_ephemeral_volume(self):
        mapped = False
        if not self.args.devices:
            if self.args.encryptionKey:
                if os.path.exists("/dev/mapper/essdb"):
                    self.args.devices = ["essdb"]
                    mapped = True
                elif os.path.exists("/dev/mapper/essda2"):
                    self.args.devices = ["essda2"]
                    mapped = True

            if not mapped:
                if os.path.exists("/dev/sdb"):
                    self.args.devices = ["sdb"]
                else:
                    self.args.devices = ["sda2"]

        if self.args.encryptionKey is None:
            device_mappings = utils.get_device_mappings(self.conf)
            for dm in device_mappings:
                if dm["device_id"] == self.args.devices[0]:
                    if dm["file_system"] == self.args.fileSystem:
                        return 0

                    if not os.path.exists(dm["mount_point"]):
                        return 21
                    if not os.path.isdir(dm["mount_point"]):
                        return 22

                    if len(os.listdir(dm["mount_point"])) > 0:
                        return 0

                    utils.unmount(self.conf, dm["mount_point"])
                    self.format(self.args.devices[0])
            utils.mount(self.conf,
                        self.args.devices[0],
                        self.args.fileSystem,
                        self.args.mountPoint)
        else:
            key_file_path = None
            try:
                key_file_path = self.write_key_file(False)

                unencrypted_mount = None
                encrypted_mount = None
                encrypted_device_id = "es" + self.args.devices[0]
                device_mappings = utils.get_device_mappings(self.conf)
                for dm in device_mappings:
                    if dm["device_id"] ==  self.args.devices[0]:
                        if dm["device_type"] != utils.DeviceTypes.EPHEMERAL:
                            raise exceptions.AgentJobException(
                                "Attempt to mount non-ephemeral device " +
                                self.args.devices[0] + " as an ephemeral mount.")
                        if dm["encrypted"]:
                            unencrypted_mount = dm
                    elif encrypted_device_id == dm["device_id"]:
                        if dm["encrypted"]:
                            encrypted_mount = dm
                if unencrypted_mount is None and encrypted_mount is None:
                    utils.open_encrypted_device(self.conf,
                                                self.args.devices[0],
                                                encrypted_device_id,
                                                key_file_path)

                    utils.mount(self.conf, encrypted_device_id,
                                self.args.fileSystem, self.args.mountPoint)
                elif unencrypted_mount is None:
                    utils.unmount(self.args.mountPoint)
                    self.setup_encryption(self.args.devices[0],
                                          encrypted_device_id,
                                          key_file_path)
                    utils.open_encrypted_device(self.conf,
                                                self.args.devices[0],
                                                encrypted_device_id,
                                                key_file_path)
                    self.format(encrypted_device_id)
                    self.mount(encrypted_device_id)
            finally:
                utils.safe_delete(key_file_path)

    def setup_encryption(self, device_id, encrypted_device_id, key_file_path):
        command = [self.conf.get_script_location("setupEncryption"),
                   device_id,
                   encrypted_device_id,
                   key_file_path]
        (stdout, stderr, rc) = utils.run_command(self.conf, command)
        if rc != 0:
            raise exceptions.AgentExecutableException("format failed: " + stderr)
        return rc

    def write_key_file(self, block_device):
        if self.args.encryptionKey is None:
            return None

        if block_device:
            key_file_dir = self.conf.storage_temppath
        else:
            key_file_dir = os.path.join(self.conf.storage_base_dir, "tmp")
        key_file_path = os.path.join(key_file_dir, "fskey.txt")

        with open(key_file_path, "w") as fptr:
            fptr.write(self.args.encryptionKey.decode("utf-8"))

        return key_file_path

    def format(self, device_id):
        return utils.format(
            self.conf, device_id, self.args.fileSystem,
            self.args.mountPoint, self.args.encryptionKey)

    def configureRaid(self, device_id):
        if self.args.formatVolume:
            exe = self.conf.get_script_location("configureRaid")
        else:
            exe = self.conf.get_script_location("assembleRaid")

        cmd = [exe, device_id]

        for d in self.args.devices:
            cmd.append(d)

        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
        if rc != 0:
            raise exceptions.AgentExecutableException("format failed: " + stderr)
        return rc

    def mount_no_fs(self):
        device_mappings = utils.get_device_mappings(self.conf)

        for device in self.args.devices:
            for mapping in device_mappings:
                d_id = mapping["device_id"]
                mount_point = mapping["mount_point"]
                if d_id == device:
                    utils.unmount(self.conf, mount_point)
                    break

    def mount_block_volume(self):
        if not self.args.devices:
            return 0

        if len(self.args.devices) > 1 and self.args.raidLevel.upper() == "NONE":
            raise exceptions.AgentJobException(
                "Must specify a RAID volume with mounting multiple devices at "
                "once.")

        if len(self.args.devices) > 1:
            target_device = "md0"
        else:
            target_device = self.args.devices[0]

        td = target_device
        if self.args.encryptionKey is not None:
            encrypted_device = "es" + target_device
            td = encrypted_device

        device_mappings = utils.get_device_mappings(self.conf)
        for mapping in device_mappings:
            if mapping["device_id"] == td:
                return 0

        if len(self.args.devices) > 1:
            self.configure_raid(target_device)

        if self.args.formatVolume:
            if self.args.encryptionKey:
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
        elif self.args.encryptionKey:
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
        if self.args.encryptionKey is not None:
            utils.mount(target_device, self.args.fileSystem, self.args.mountPoint)

    def run(self):
        if self.args.mountPoint is None:
            self.args.mountPoint = self.conf.storage_operations_path

        if self.args.fileSystem is None:
            self.args.fileSystem = self.conf.storage_default_file_system

        if self.args.fileSystem is None:
            self.mount_no_fs()
        elif self.args.raidLevel is None:
            self.mount_ephemeral_volume()
        else:
            self.mount_block_volume()

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return MountVolume(conf, job_id, items_map, name, arguments)
