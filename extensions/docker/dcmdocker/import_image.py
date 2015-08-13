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
import json
import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class ImportImage(docker_utils.DockerJob):

    protocol_arguments = {
        "src": ("", True, str, None),
        "repository": ("", False, str, None),
        "tag": ("", False, str, None),
        "image": ("", False, str, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ImportImage, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        out = self.docker_conn.import_image(
            src=self.args.src, repository=self.args.repository,
            tag=self.args.tag, image=self.args.image)
        out = json.loads(out)
        return plugin_base.PluginReply(
            0, reply_type="docker_import_image", reply_object=out)


def load_plugin(conf, job_id, items_map, name, arguments):
    return ImportImage(conf, job_id, items_map, name, arguments)
