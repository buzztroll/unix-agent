

class PluginInterface(object):

    def call(self, name, logger, arguments, **kwargs):
        pass

    def cancel(self, reply_rpc, *args, **kwargs):
        pass

    def get_name(self):
        pass