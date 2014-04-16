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
from dcm.agent import longrunners

import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class GetJobDescription(jobs.Plugin):

    protocol_arguments = {
        "jobId":
            ("The ID of job that is being queried.",
             True, str),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetJobDescription, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        job_id = self.arguments["jobId"]
        lr = self.items_map["long_runner"]
        job_description = lr.lookup_job(job_id)
        if job_description is None:
            return {'return_code': 1, 'message': "no such job id %d" % job_id}
        return {'return_code': 0,
                'reply_object': job_description.get_message_payload(),
                'reply_type': 'job_description'}

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return GetJobDescription(conf, job_id, items_map, name, arguments)
