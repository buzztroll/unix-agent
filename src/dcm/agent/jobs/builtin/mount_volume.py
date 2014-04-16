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
        pass

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
        pass

    def run(self):

        mount_point = self.conf.storage_operations_path
        fs = self.conf.storage_default_file_system

        device_str = ""
        if not self.args.devices:
            device_str = "--"
        else:
            delim = ""
            for d in self.args.devices:
                device_str = delim + device_str
                delim = ","

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
