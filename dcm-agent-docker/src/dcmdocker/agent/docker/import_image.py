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


class ImportImage(docker_utils.DockerJob):

    protocol_arguments = {
        "src": ("", True, str, None),
        "repository": ("", True, str, None),
        "tag": ("", False, str, None),
        "image": ("", False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ImportImage, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.import_image(
            src=self.args.src, repository=self.args.repository,
            tag=self.args.tags, image=self.args.image)
        reply_doc = {
            "return_code": 0,
            "reply_type": "docker_import_image",
            "reply_object": out
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return ImportImage(conf, job_id, items_map, name, arguments)
