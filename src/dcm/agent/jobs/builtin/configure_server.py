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
from dcm.agent import exceptions, utils
import dcm.agent.jobs as jobs
from dcm.agent import config
from dcm.agent.cmd import configure as cfg


_g_logger = logging.getLogger(__name__)

_g_platform_dep_installer = {
    config.PLATFORM_TYPES.PLATFORM_RHEL: ["rpmInstall", "puppet"],
    config.PLATFORM_TYPES.PLATFORM_UBUNTU: ["debInstall", "puppet"],
    config.PLATFORM_TYPES.PLATFORM_DEBIAN: ["debInstall", "puppet"]
}


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

    def _edit_puppet_conf(self, path):
        puppet_conf_temp = self.conf.get_temp_file("puppet.conf")

        with open(path, "r") as inf, open(puppet_conf_temp, "w") as outf:
            outf.writelines([l.strip() + os.linesep for l in inf.readlines()])

        parser = ConfigParser.SafeConfigParser()
        parser.read(puppet_conf_temp)

        if not parser.has_section("agent"):
            parser.add_section("agent")
        parser.set("agent", "certname", "ES_NODE_NAME")
        parser.set("agent", "server", "ES_PUPPET_MASTER")
        if not parser.has_section("main"):
            parser.add_section("main")
        parser.set("main", "pluginsync", "true")

        with open(puppet_conf_temp, "w") as fptr:
            parser.write(fptr)
        return puppet_conf_temp

    def configure_server_with_puppet(self):
        distro, version = utils.identify_platform(self.conf)
        config_files = cfg.get_config_files()
        if not utils.extras_installed(distro, cfg):
            for cf in config_files:
                parser = ConfigParser.SafeConfigParser()
                parser.read(cf)
                if parser.has_section('extras'):
                    try:
                        location = parser.get('extras', 'location')
                    except ConfigParser.NoOptionError as e:
                        _g_logger.debug("Error reading config file with option %s"
                                        % 'location')
                        _g_logger.debug("Exception is %s " % e._get_message)
                else:
                    location = 'http://s3.amazonaws.com/dcmagentnightly/'
                    _g_logger.info("Runnig with location = %s" % location)

            try:
                cfg.install_extras(location, distro, version, package=None)
            except exceptions.AgentExtrasNotInstalledException as ex:
                _g_logger.exception("An error occurred trying to install puppet.  "
                                    "We are continuing anyway for legacy server "
                                    "images")
                _g_logger.exception("Exception message is %s" % ex.message)

        puppet_conf_file_list = ["/etc/puppet/puppet.conf",
                                 "/etc/puppetlabs/puppet/puppet.conf"]
        new_puppet_conf = None
        for puppet_conf_file in puppet_conf_file_list:
            if os.path.exists(puppet_conf_file):
                new_puppet_conf = self._edit_puppet_conf(puppet_conf_file)
                break

        puppet_dir = self.conf.get_temp_file("puppetconf", isdir=True)
        cert_file_path = self.conf.get_temp_file("cert.pem")
        key_file_path = self.conf.get_temp_file("key.pem")

        try:
            with open(cert_file_path, "w") as fptr:
                fptr.write(self.args.configCert)
            with open(key_file_path, "w") as fptr:
                fptr.write(self.args.configKey)

            endpoint = self.args.endpoint
            if endpoint is None:
                endpoint = "NULL"

            exe = self.conf.get_script_location(
                "runConfigurationManagement-PUPPET")
            cmd = [exe,
                   self.args.runAsUser,
                   self.args.configClientName,
                   endpoint,
                   cert_file_path,
                   key_file_path]
            if new_puppet_conf:
                cmd.append(new_puppet_conf)
            return utils.run_command(self.conf, cmd)
        finally:
            utils.safe_delete(puppet_dir)
            utils.safe_delete(cert_file_path)
            utils.safe_delete(key_file_path)

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
