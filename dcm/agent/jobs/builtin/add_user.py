import os
import dcm.agent.util as util
import dcm.agent.exceptions as exceptions
import dcm.agent.jobs as jobs


class AddUser(jobs.Plugin):

    def __init__(self, agent, conf, job_id, items_map, name, arguments):
        super(AddUser, self).__init__(
            agent, conf, job_id, items_map, name, arguments)
        try:
            self.user_id = arguments['user_id']
            self.first_name = arguments['first_name']
            self.last_name = arguments['last_name']
            self.ssh_public_key = arguments['ssh_public_key']
            self.administrator = arguments['administrator']
            self.agent = agent
        except KeyError as ke:
            raise exceptions.AgentPluginMessageException(
                "The command %s requires the argument %s" % (name, ke.message))

        if 'password' not in arguments['password']:
            self.password = util.generate_password()
        else:
            self.password = arguments['password']

        try:
            self.add_user_exe_path = items_map['add_user_exe_path']
            if not os.path.exists(self.add_user_exe_path):
                raise exceptions.AgentPluginConfigException(
                    "The plugin %s points an add_user_exe_path that does not "
                    "exist." % name)
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, ke.message))

    def call(self):

        key_file = self.agent.get_temp_file(self.user_id + ".pub")

        command_line = [self.add_user_exe_path,
                        self.agent.get_customer_id(),
                        self.user_id,
                        self.first_name,
                        self.last_name,
                        self.administrator,
                        self.password]

        try:
            with open(key_file, "w") as f:
                f.write(self.ssh_public_key)
            rc = util.fork_exe(command_line, self.logger)
            return rc
        except:
            # TODO do something here
            raise
        finally:
            os.remove(key_file)

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(agent, conf, job_id, items_map, name, arguments):
    return AddUser(agent, conf, job_id, items_map, name, arguments)
