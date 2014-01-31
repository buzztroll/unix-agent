import dcm.agent.utils as agent_util


class PluginInterface(object):

    @agent_util.not_implemented_decorator
    def call(self, name, logger, arguments, **kwargs):
        pass

    @agent_util.not_implemented_decorator
    def cancel(self, reply_rpc, *args, **kwargs):
        pass

    @agent_util.not_implemented_decorator
    def get_name(self):
        pass
