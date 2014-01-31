import os
import dcm.agent.utils as utils
import dcm.agent.jobs.builtin.direct_pass as direct_pass


class AddUser(direct_pass.DirectPass):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(AddUser, self).__init__(
            conf, job_id, items_map, name, arguments)

        self._ordered_param_list = [conf.customer_id,
                                    "user_id",
                                    "first_name",
                                    "last_name",
                                    "administrator",
                                    "password"]

        if 'password' not in arguments['password'] or not arguments['password']:
            self.arguments["password"] = utils.generate_password()

    def call(self):
        key_file = self.agent.get_temp_file(self.user_id + ".pub")

        try:
            with open(key_file, "w") as f:
                f.write(self.ssh_public_key)
            return super(AddUser, self).call()
        finally:
            os.remove(key_file)

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return AddUser(conf, job_id, items_map, name, arguments)
