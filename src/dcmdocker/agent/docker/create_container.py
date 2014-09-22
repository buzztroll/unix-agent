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

import dcm.agent.docker.utils as docker_utils


class DockerCreateContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "image": ("", True, str, None),
        "command": ("", False, str, None),
        "hostname": ("", False, str, None),
        "user": ("", False, str, None),
        "mem_limit": ("", False, int, 0),
        "ports": ("", False, list, None),
        "environment": ("", False, dict, None),
        "memswap_limit": ("", False, int, 0),
        "name": ("", False, str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DockerCreateContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.create_container(
            self.args.image,
            command=self.args.command,
            hostname=self.args.hostname,
            user=self.args.user,
            detach=True,
            stdin_open=False,
            tty=False,
            mem_limit=self.args.mem_limit,
            ports=self.args.ports,
            environment=self.args.environment,
            dns=None,
            volumes=None,
            volumes_from=None,
            network_disabled=False,
            name=self.args.name,
            entrypoint=None,
            cpu_shares=None,
            working_dir=None,
            memswap_limit=self.args.memswap_limit)
        reply_doc = {
            "return_code": 0,
            "reply_type": "docker_create_container",
            "reply_object": out
        }
        return reply_doc



def load_plugin(conf, job_id, items_map, name, arguments):
    return DockerCreateContainer(conf, job_id, items_map, name, arguments)
