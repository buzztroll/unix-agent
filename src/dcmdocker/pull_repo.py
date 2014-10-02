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
import json
import logging
from dcm.agent import utils

import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class PullRepo(docker_utils.DockerJob):

    protocol_arguments = {
        "repository": ("", True, str, None),
        "tag": ("", False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(PullRepo, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.pull(
            self.args.repository, tag=self.args.tag, stream=True)

        # only log the last line at info level
        id_map = {}
        for line in out:
            j_obj = json.loads(line)
            id_map[j_obj['id']] = line
            _g_logger.debug(line)
        for k in id_map:
            utils.log_to_dcm(logging.INFO, id_map[k])
        reply_doc = {
            "return_code": 0,
            "reply_type": "docker_pull",
            "reply_object": None
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return PullRepo(conf, job_id, items_map, name, arguments)
