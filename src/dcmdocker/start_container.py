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

import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class StartContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "port_bindings": ("", False, dict, None),
        "lxc_conf": ("", False, list, None),
        "links": ("", False, dict, None),
        "privileged": ("", False, bool, False),
        "publish_all_ports": ("", False, bool, False),
        "cap_add": ("", False, list, None),
        "cap_drop": ("", False, list, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(StartContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        # make a list a tuple
        if self.args.port_bindings:
            for internal_port in self.args.port_bindings:
                binding_list = self.args.port_bindings[internal_port]
                new_binding_list = []
                for bind in binding_list:
                    host, port = bind
                    new_binding_list.append((host, port,))
                self.args.port_bindings[internal_port] = new_binding_list

        self.docker_conn.start(self.args.container,
                               port_bindings=self.args.port_bindings,
                               lxc_conf=self.args.lxc_conf,
                               links=self.args.links,
                               privileged=self.args.privileged,
                               publish_all_ports=self.args.publish_all_ports,
                               cap_add=self.args.cap_add,
                               cap_drop=self.args.cap_drop,
                               network_mode="bridge")
        reply_doc = {
            "return_code": 0,
            "reply_type": "void",
            "reply_object": None
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return StartContainer(conf, job_id, items_map, name, arguments)
