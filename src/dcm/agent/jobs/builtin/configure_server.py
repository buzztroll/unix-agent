# ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================
import ConfigParser
import json
import logging
import os
import urlparse

import dcm.agent.exceptions as exceptions
import dcm.agent.jobs as jobs
import dcm.agent.utils as utils


_g_logger = logging.getLogger(__name__)


class ConfigureServer(jobs.Plugin):
    protocol_arguments = {
        "configType":
            ("", True, str, None),
        "authId":
            ("", False, str, None),
        "configurationData":
            ("", False, utils.base64type_convertor, None),
        "encryptedConfigToken":
            ("", False, utils.base64type_convertor, None),
        "encryptedAuthSecret":
            ("", False, utils.base64type_convertor, None),
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
            ("", False, utils.base64type_convertor, None),
        "storagePrivateKey":
            ("", False, utils.base64type_convertor, None),
        "environmentId":
            ("", False, str, None),
        "personalityFiles":
            ("", False, list, None),
        "configClientName":
            ("", False, str, None),
        "configCert":
            ("", False, utils.base64type_convertor, None),
        "configKey":
            ("", False, utils.base64type_convertor, None),
        "runListIds":
            ("", False, list, None),
        "parameterList":
            ("", False, utils.base64type_convertor, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ConfigureServer, self).__init__(
            conf, job_id, items_map, name, arguments)
        if not self.args.runAsUser:
            self.args.runAsUser = self.conf.system_user

    def configure_server_legacy(self):
        """
        This will handle protocol 0 and protocol 15
        """
        cfg_file_path = self.conf.get_temp_file("configManagement.cfg")
        token_file_path = self.conf.get_temp_file("token.pem")

        auth_id = self.args.authId
        endpoint = self.args.endpoint

        # set the token
        if self.args.configToken:
            token = self.args.configToken
        elif self.args.encryptedAuthSecret:
            token = self.args.encryptedAuthSecret
        else:
            token = None

        try:
            with open(cfg_file_path, "w") as fptr:
                fptr.write(self.args.configurationData)

            if token:
                with open(token_file_path, "w") as fptr:
                    fptr.write(token)
                    fptr.write(os.linesep)

            # run the figure program
            exe_name = "runConfigurationManagement-" + self.args.configType
            exe = self.conf.get_script_location(exe_name)
            cmd = [exe,
                   self.args.runAsUser,
                   token_file_path,
                   cfg_file_path,
                   auth_id,
                   endpoint]
            return utils.run_command(self.conf, cmd)
        finally:
            utils.safe_delete(cfg_file_path)
            utils.safe_delete(token_file_path)

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
                        environmentId]
            return utils.run_command(self.conf, cmd_list)
        finally:
            utils.safe_delete(run_list_file_name)
            utils.safe_delete(token_file_path)

    def _edit_puppet_conf(self, template_path, new_location, endpoint):
        parser = ConfigParser.SafeConfigParser()
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
        endpoint = urlparse.urlparse(self.args.endpoint).hostname

        puppet_extras_base_path = os.path.join(self.conf.extra_base_path,
                                               "puppetconf")
        puppet_extras_bin = os.path.join(self.conf.extra_base_path,
                                         "bin/puppet")

        try:
            utils.install_extras(
                self.conf, package=self.conf.extra_package_name)
        except exceptions.AgentExtrasNotInstalledException as ex:
            _g_logger.exception("An error occurred trying to install puppet.  "
                                "Exception message is %s" % ex.message)
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
            return utils.run_command(self.conf, cmd)
        finally:
            utils.safe_delete(cert_file_path)
            utils.safe_delete(key_file_path)
            utils.safe_delete(puppet_conf_path)

    def run(self):
        if self.conf.is_imaging():
            raise exceptions.AgentPluginOperationIsImagingException(
                operation_name=self.name)

        _g_logger.info("Running configuration management of type " +
                       self.args.configType)

        if self.args.configType.upper() == "ENSTRATUS":
            raise exceptions.AgentOptionException(
                "configType", "CHEF or PUPPET", self.args.configType)

        if self.name == "configure_server" or \
                self.name == "configure_server_15":
            (stdout, stderr, rc) = self.configure_server_legacy()
        elif self.name == "configure_server_16":
            (stdout, stderr, rc) = self.configure_server_legacy()
        else:
            if self.args.configType.upper() == "CHEF":
                (stdout, stderr, rc) = self.configure_server_with_chef()
            elif self.args.configType.upper() == "PUPPET":
                (stdout, stderr, rc) = self.configure_server_with_puppet()
            else:
                rc = 1
                stderr = "The type %s is not supported." % self.args.configType
                stdout = ""

        if rc != 0:
            reply_doc = {"return_code": rc,
                         "message": stderr}
        else:
            reply_doc = {"return_code": rc,
                         "reply_type": "string",
                         "reply_object": stdout}
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return ConfigureServer(conf, job_id, items_map, name, arguments)
