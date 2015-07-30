import datetime

import dcm.agent.plugins.api.base as plugin_base


class GetTimeExample(plugin_base.Plugin):
    command_name = "get_time_example"

    def run(self):
        tm = datetime.datetime.now()

        reply_doc = {
            "return_code": 0,
            "reply_type": "string",
            "reply_object": str(tm)
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return GetTimeExample(conf, job_id, items_map, name, arguments)
