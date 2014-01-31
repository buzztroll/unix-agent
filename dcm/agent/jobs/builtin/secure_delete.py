import os
import dcm.agent.jobs.builtin.direct_pass as direct_pass


class SecureDelete(direct_pass.DirectPass):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(SecureDelete, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._ordered_param_list = ["fileName"]

    def call(self):
        reply = super(SecureDelete, self).call()
        filename = self.arguments["fileName"]

        # TODO figure out why the java code did this
        # touch the file
        if os.path.exists(filename):
            os.remove(filename)


def load_plugin(conf, job_id, items_map, name, arguments):
    return SecureDelete(conf, job_id, items_map, name, arguments)
