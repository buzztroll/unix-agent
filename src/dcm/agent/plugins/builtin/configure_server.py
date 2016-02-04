#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import configparser
import json
import logging
import os
import urllib.parse

import dcm.agent.exceptions as exceptions
import dcm.agent.logger as dcm_logger
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.exceptions as plugin_exceptions
import dcm.agent.plugins.api.utils as plugin_utils
import dcm.agent.utils as utils


_g_logger = logging.getLogger(__name__)


class ConfigureServer(plugin_base.Plugin):
    protocol_arguments = {
        "configType":
            ("Which configuration management software to use (chef or puppet)",
             True, str, None),
        "authId":
            ("", False, str, None),
        "configurationData":
            ("", False, plugin_utils.base64type_convertor, None),
        "encryptedConfigToken":
            ("", False, plugin_utils.base64type_convertor, None),
        "encryptedAuthSecret":
            ("", False, plugin_utils.base64type_convertor, None),
        "endpoint":
            ("", False, str, None),
        "providerRegionId":
            ("", False, str, None),
        "runAsUser":
            ("", False, str, None),
        "storageDelegate":
            ("", False, str, None),
        "storageEndpoint":
            ("", False, str, None),
        "storageAccount":
            ("", False, str, None),
        "scriptFiles":
            ("", False, list, None),
        "storagePublicKey":
            ("", False, plugin_utils.base64type_convertor, None),
        "storagePrivateKey":
            ("", False, plugin_utils.base64type_convertor, None),
        "environmentId":
            ("", False, str, None),
        "personalityFiles":
            ("", False, list, None),
        "configClientName":
            ("", False, str, None),
        "configCert":
            ("", False, plugin_utils.base64type_convertor, None),
        "configKey":
            ("", False, plugin_utils.base64type_convertor, None),
        "runListIds":
            ("", False, list, None),
        "parameterList":
            ("", False, plugin_utils.base64type_convertor, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ConfigureServer, self).__init__(
            conf, job_id, items_map, name, arguments)
        if not self.args.runAsUser:
            self.args.runAsUser = self.conf.system_user

    def configure_server_with_chef(self):
        chef_dir = self.conf.get_temp_file("chefconf", isdir=True)
        run_list_file_name = os.path.join(chef_dir, "runList.cfg")
        token_file_path = self.conf.get_temp_file("token.pem")

        try:
            if self.args.encryptedAuthSecret:
                token = self.args.encryptedAuthSecret
            else:
                token = "NULL"

            authId = self.args.authId
            if authId is None:
                authId = "NULL"

            endpoint = self.args.endpoint
            if endpoint is None:
                endpoint = "NULL"
            environmentId = self.args.environmentId
            if environmentId is None:
                environmentId = "NULL"
            chef_json = {"run_list": self.args.runListIds}
            with open(run_list_file_name, "w") as fptr:
                fptr.write(json.dumps(chef_json))

            with open(token_file_path, "w") as fptr:
                fptr.write(token)
                fptr.write(os.linesep)

            exe = self.conf.get_script_location(
                "runConfigurationManagement-CHEF")
            cmd_list = [exe,
                        self.args.runAsUser,
                        self.args.configClientName,
                        token_file_path,
                        run_list_file_name,
                        authId,
                        endpoint,
                        environmentId,
                        self.conf.configuration_management_chef_client_version]
            return plugin_utils.run_command(self.conf, cmd_list)
        finally:
            plugin_utils.safe_delete(run_list_file_name)
            plugin_utils.safe_delete(token_file_path)

    def _edit_puppet_conf(self, template_path, new_location, endpoint):
        parser = configparser.SafeConfigParser()
        parser.read(template_path)
        if not parser.has_section("agent"):
            parser.add_section("agent")
        parser.set("agent", "certname", self.args.configClientName)
        parser.set("agent", "server", endpoint)
        with open(new_location, "w") as fptr:
            parser.write(fptr)

    def configure_server_with_puppet(self):

        if self.args.endpoint is None:
            raise exceptions.AgentOptionValueNotSetException("endpoint")

        # XXX it will only work with the default port.  There is no way for
        # the user to configure anything else in the console
        endpoint = urllib.parse.urlparse(self.args.endpoint).hostname

        puppet_extras_base_path = os.path.join(self.conf.extra_base_path,
                                               "puppetconf")
        puppet_extras_bin = os.path.join(self.conf.extra_base_path,
                                         "bin/puppet")

        try:
            utils.install_extras(
                self.conf, package=self.conf.extra_package_name)
        except exceptions.AgentExtrasNotInstalledException as ex:
            _g_logger.exception("An error occurred trying to install puppet.  "
                                "Exception message is %s" % str(ex))
            raise

        template_puppet_conf_path = os.path.join(puppet_extras_base_path,
                                                 "puppet.conf.template")
        if not os.path.exists(template_puppet_conf_path):
            raise exceptions.AgentExtrasNotInstalledException(
                "The puppet.conf template did not install properly.")
        if not os.path.exists(puppet_extras_bin):
            raise exceptions.AgentExtrasNotInstalledException(
                "The puppet binary did not install properly.")

        puppet_conf_path = self.conf.get_temp_file("puppet.conf")
        self._edit_puppet_conf(template_puppet_conf_path,
                               puppet_conf_path,
                               endpoint)
        cert_file_path = self.conf.get_temp_file("cert.pem")
        key_file_path = self.conf.get_temp_file("key.pem")

        try:
            with open(cert_file_path, "w") as fptr:
                fptr.write(self.args.configCert)
            with open(key_file_path, "w") as fptr:
                fptr.write(self.args.configKey)

            exe = self.conf.get_script_location(
                "runConfigurationManagement-PUPPET")
            cmd = [exe,
                   endpoint,
                   cert_file_path,
                   key_file_path,
                   self.args.configClientName,
                   self.conf.extra_base_path,
                   puppet_conf_path]
            return plugin_utils.run_command(self.conf, cmd)
        finally:
            plugin_utils.safe_delete(cert_file_path)
            plugin_utils.safe_delete(key_file_path)
            plugin_utils.safe_delete(puppet_conf_path)

    def run(self):
        _g_logger.info("Running configuration management of type " +
                       self.args.configType)

        if self.args.configType.upper() == "CHEF":
            (stdout, stderr, rc) = self.configure_server_with_chef()
        elif self.args.configType.upper() == "PUPPET":
            (stdout, stderr, rc) = self.configure_server_with_puppet()
        else:
            raise plugin_exceptions.AgentPluginParameterBadValueException(
                "configType", "CHEF or PUPPET")

        if stderr:
            dcm_logger.log_to_dcm_console_configuration_management_error(
                stderr=stderr)
        if stdout:
            dcm_logger.log_to_dcm_console_configuration_management_output(
                stdout=stdout)

        if rc != 0:
            return plugin_base.PluginReply(rc, message=stderr)
        else:
            return plugin_base.PluginReply(
                rc, reply_type="string", reply_object=stdout)


def load_plugin(conf, job_id, items_map, name, arguments):
    return ConfigureServer(conf, job_id, items_map, name, arguments)
