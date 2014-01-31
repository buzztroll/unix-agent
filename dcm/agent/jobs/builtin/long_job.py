import logging

import dcm.agent.jobs as jobs
import dcm.agent.longrunners as longjobs


_g_logger = logging.getLogger(__name__)


class LongJob(jobs.Plugin):

    def __init__(self, conf, request_id, items_map, name, arguments):
        super(LongJob, self).__init__(
            conf, request_id, items_map, name, arguments)

    def run(self):
        detached_job = longjobs.start_new_job(self, self.name, self.arguments)
        reply_object = detached_job.get_message_payload()
        return {'return_code': 0,
                'reply_object': reply_object,
                'reply_type': 'job_description'}


    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, request_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return LongJob(conf, request_id, items_map, name, arguments)
