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

import dcm.agent.utils as utils
import dcm.agent.jobs as jobs


class DeviceTypes(object):
    ROOT = "ROOT"
    EPHEMERAL = "EPHEMERAL"
    SERVICE = "SERVICE"
    CUSTOM = "CUSTOM"


class GetDeviceMappings(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetDeviceMappings, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name)]

    def run(self):
        (stdout, stderr, rc) = utils.run_command(self.conf, self.command)
        if rc != 0:
            reply_doc = {
                "return_code": rc,
                "message": stderr
            }
            return reply_doc

        device_mapping_list = []
        lines = stdout.split(os.linesep)
        for line in lines:
            parts = line.split()
            if len(parts) != 5:
                continue

            elements = parts[0].split("/")
            device_id = elements[len(elements) - 1]
            file_system = parts[1]
            mount_point = parts[2]
            size = int(parts[3])
            used = int(parts[4])
            if parts[0].startswith("/dev/mapper"):
                encrypted = True
            else:
                encrypted = False

            if mount_point == "/":
                type = DeviceTypes.ROOT
            elif mount_point == self.conf.services_path:
                type = DeviceTypes.SERVICE
            elif mount_point == self.conf.ephemeral_mount_point:
                type = DeviceTypes.EPHEMERAL
            else:
                type = DeviceTypes.CUSTOM

            device_mapping = {
                "device_id": device_id,
                "encrypted": encrypted,
                "file_system": file_system,
                "mount_point": mount_point,
                "size":  size,
                "used": used,
                "device_type": type
            }
            device_mapping_list.append(device_mapping)

        reply_doc = {
            "return_code": 0,
            "reply_type": stderr,
            "reply_object": device_mapping_list
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetDeviceMappings(conf, job_id, items_map, name, arguments)
