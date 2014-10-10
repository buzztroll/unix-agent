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
import uuid
from dcm.agent.jobs import pages


_g_logger = logging.getLogger(__name__)


class GetLogContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "stdout": ("", False, bool, True),
        "stderr": ("", False, bool, False),
        "timestamps": ("", False, bool, False),
        "page_token": ("", False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetLogContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        if self.args.page_token is None:
            out = self.docker_conn.logs(self.args.container,
                                        stdout=self.args.stdout,
                                        stderr=self.args.stderr,
                                        stream=False,
                                        timestamps=self.args.timestamps)
            token = str(uuid.uuid4()).replace("-", "")
            pager = pages.StringPage(12*1024, out)
            self.conf.page_monitor.new_pager(pager, token)
        else:
            token = self.args.page_token

        page, token = self.conf.page_monitor.get_next_page(token)
        out = {'next_token': token, 'log_data': page}

        reply_doc = {
            "return_code": 0,
            "reply_type": "docker_logs",
            "reply_object": out
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetLogContainer(conf, job_id, items_map, name, arguments)
