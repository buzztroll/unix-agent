import time

import dcm.agent.plugins.api.base as plugin_base


class CountSleepExample(plugin_base.Plugin):
    protocol_arguments = {
        "count": ("The number of times to loop and sleep", True, int, 10),
        "sleepTime": ("The number of seconds to sleep ever iteration",
                      True, float, 1.0)
    }
    long_runner = True
    command_name = "count_sleep_example"

    def run(self):
        for _ in range(self.args.count):
            time.sleep(self.args.sleepTime)

        reply_doc = {
            "return_code": 0,
            "reply_type": "void",
            "reply_object": None
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return CountSleepExample(conf, job_id, items_map, name, arguments)
