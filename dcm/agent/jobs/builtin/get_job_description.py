import logging
from dcm.agent import longrunners

import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class GetJobDescription(jobs.Plugin):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetJobDescription, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        job_id = self.arguments["jobId"]
        job_description = longrunners.lookup_job(job_id)
        if job_description is None:
            return {'return_code': 1, 'message': "no such job id %d" % job_id}
        return {'return_code': 0,
                'payload': job_description.get_message_payload()}

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return GetJobDescription(conf, job_id, items_map, name, arguments)
