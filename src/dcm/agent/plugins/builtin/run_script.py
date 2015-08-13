import hashlib
import logging
import os
import sys
import zlib

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.exceptions as plugin_exceptions
import dcm.agent.plugins.api.utils as plugin_utils


_g_logger = logging.getLogger(__name__)


_g_compression_map = {
    'gzip': zlib.decompress
}


class RunScript(plugin_base.Plugin):

    protocol_arguments = {
        "b64script": ("A base64 encoded executable.", True,
                      plugin_utils.base64type_binary_convertor, None),
        "checksum": ("The checksum of the script.", True, str, None),
        "inpython": ("Run this script with the current python environment.",
                     False, bool, False),
        "runUnderSudo": ("Run this script as the root use with sudo.",
                         False, bool, False),
        "compression": ("A string to determine what type of compression was"
                        "used on the incoming script.",
                        False, str, None),
        "arguments": ("The list of arguments to be passed to the script",
                      False, list, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RunScript, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        script_file = self.conf.get_temp_file("exe_script")
        data = self.args.b64script
        if self.args.compression:
            if self.args.compression not in _g_compression_map:
                raise plugin_exceptions.AgentPluginBadParameterException(
                    'compression',
                    "The value % is not a supported compression module")
            data = _g_compression_map[self.args.compression](data)
        sha256 = hashlib.sha256()
        sha256.update(data)
        actual_checksum = sha256.hexdigest()
        if actual_checksum != self.args.checksum:
            raise plugin_exceptions.AgentPluginOperationException(
                "The checksum did not match")
        try:
            with open(script_file, "wb") as f:
                f.write(data)
            os.chmod(script_file, 0o755)

            command_list = []
            if self.args.runUnderSudo:
                command_list.append(self.conf.system_sudo)
            if self.args.inpython:
                command_list.append(sys.executable)
            command_list.append(script_file)
            if self.args.arguments:
                command_list.extend(self.args.arguments)
            _g_logger.debug("Plugin running the command %s"
                            % str(command_list))
            (stdout, stderr, rc) = plugin_utils.run_command(
                self.conf, command_list)
            _g_logger.debug("Command %s: stdout %s.  stderr: %s" %
                            (str(command_list), stdout, stderr))
            return plugin_base.PluginReply(
                rc, message=stdout, error_message=stderr, reply_type="void")
        finally:
            if os.path.exists(script_file):
                os.remove(script_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return RunScript(conf, job_id, items_map, name, arguments)
