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


class DeleteImages(docker_utils.DockerJob):

    protocol_arguments = {
        "name": ("", True, str, None),
        "force": ("", False, bool, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DeleteImages, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        self.docker_conn.remove_image(self.args.name)
        reply_doc = {
            "return_code": 0,
            "reply_type": "void",
            "reply_object": None
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return DeleteImages(conf, job_id, items_map, name, arguments)
