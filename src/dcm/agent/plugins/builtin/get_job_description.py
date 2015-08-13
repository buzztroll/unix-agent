#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging

import dcm.agent.plugins.api.base as plugin_base


_g_logger = logging.getLogger(__name__)


class GetJobDescription(plugin_base.Plugin):

    protocol_arguments = {
        "jobId":
        ("The ID of job that is being queried.",
         True, str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetJobDescription, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        job_id = self.arguments["jobId"]
        lr = self.items_map["long_runner"]
        job_description = lr.lookup_job(job_id)
        if job_description is None:
            msg = "no such job id %d" % job_id
            return plugin_base.PluginReply(1, message=msg, error_message=msg)

        return plugin_base.PluginReply(
            0,
            reply_object=job_description.get_message_payload(),
            reply_type='job_description')


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return GetJobDescription(conf, job_id, items_map, name, arguments)
