import os
import dcm.agent.utils as utils
import dcm.agent.exceptions as exceptions
import dcm.agent.jobs as jobs


class DirectPass(jobs.Plugin):
    """
    This plugin can be used for those scripts that need no massaging.  We
    simply take the remote arguments and look up the command and run it.
    All that subclasses need to do is set the ordered list of parameters
    for the script.
    """

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DirectPass, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._ordered_param_list = []

        try:
            script_name = items_map["script_name"]
            self.exe_path = conf.get_script_location(script_name)
            if not os.path.exists(self.add_user_exe_path):
                raise exceptions.AgentPluginConfigException(
                    "The plugin %s points an add_user_exe_path that does not "
                    "exist." % name)
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, ke.message))

    def _build_command_list(self):
        cmd_line = [self.exe_path]
        try:
            for arg_name in self._ordered_param_list:
                arg = self.arguments[arg_name]
                cmd_line.append(arg)
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, ke.message))
        return cmd_line

    def call(self):
        command_line = self._build_command_list()
        (stdout, stderr, rc) = utils.run_command(command_line)
        reply = {"return_code": rc, "message": "Success"}
        if rc != 0:
            reply["message"] = stderr
        # TODO XXX should stdout go on payload?

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return DirectPass(conf, job_id, items_map, name, arguments)
