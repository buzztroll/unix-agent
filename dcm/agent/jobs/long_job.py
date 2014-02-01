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

import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class LongJob(jobs.Plugin):

    def __init__(self, conf, request_id, items_map, name, arguments):
        super(LongJob, self).__init__(
            conf, request_id, items_map, name, arguments)
        self._long_runner = items_map["long_runner"]

    def run(self):
        detached_job = self._long_runner.start_new_job(
            self.conf,
            self.request_id,
            self.items_map,
            self.name,
            self.arguments)
        reply_object = detached_job.get_message_payload()
        return {'return_code': 0,
                'reply_object': reply_object,
                'reply_type': 'job_description'}

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, request_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return LongJob(conf, request_id, items_map, name, arguments)
