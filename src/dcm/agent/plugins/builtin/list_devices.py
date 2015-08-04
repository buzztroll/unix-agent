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
import os

import dcm.agent.exceptions as exceptions
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.utils as utils


_g_logger = logging.getLogger(__name__)


class GetDeviceMappings(plugin_base.Plugin):

    protocol_arguments = {}

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(GetDeviceMappings, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name)]

    def run(self):
        try:
            device_mapping_list = utils.get_device_mappings(self.conf)
        except exceptions.AgentExecutableException as ex:
            return plugin_base.PluginReply(1, message=str(ex))
        return plugin_base.PluginReply(
            0,
            reply_type="device_mapping_array",
            reply_object=device_mapping_list)


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetDeviceMappings(conf, job_id, items_map, name, arguments)
