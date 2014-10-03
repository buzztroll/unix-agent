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
import uuid

import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class ListImages(docker_utils.DockerJob):

    protocol_arguments = {
        "name": ("", False, str, None),
        "page_token": ("", False, str, None),
        "quiet": ("", False, bool, False),
        "all": ("", False, bool, False),
        "viz": ("", False, bool, False)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ListImages, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._message_size_limit = 14 * 1024

    def run(self):
        if self.args.page_token is None:
            out = self.docker_conn.images(name=self.args.name,
                                          quiet=self.args.quiet,
                                          all=self.args.all,
                                          viz=self.args.viz)
            token = str(uuid.uuid4()).replace("-", "")
            self.conf.page_monitor.new_json_page(out, token)
        else:
            token = self.args.page_token

        page, token = self.conf.page_monitor.get_next_page(token)
        out = {'next_token': token, 'images': page}

        reply_doc = {
            "return_code": 0,
            "reply_type": "docker_image_array",
            "reply_object": out
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return ListImages(conf, job_id, items_map, name, arguments)
