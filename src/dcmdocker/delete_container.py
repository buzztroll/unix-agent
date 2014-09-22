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

import dcmdocker.utils as docker_utils


class DeleteContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "v": ("", False, bool, False),
        "link": ("", False, bool, False),
        "force": ("", False, bool, False)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DeleteContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.remove_container(
            self.args.container, v=self.args.v,
            link=self.args.link, force=self.args.force)
        reply_doc = {
            "return_code": 0,
            "reply_type": "void",
            "reply_object": None
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return DeleteContainer(conf, job_id, items_map, name, arguments)
