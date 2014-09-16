#  ========= CONFIDENTIAL =========
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
import json
import logging
import os
import shutil
from dcm.agent import exceptions, utils, storagecloud
import dcm.agent.jobs as jobs


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

    def configure_server_with_puppet(self):
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
            return utils.run_command(self.conf, cmd)
        finally:
            utils.safe_delete(puppet_dir)
            utils.safe_delete(cert_file_path)
            utils.safe_delete(key_file_path)

    def configure_server_with_es(self):
        temp_dir = self.conf.get_temp_file("es_conf", isdir=True)
        t_stdout = ""
        t_stderr = ""
        try:
            for script_path in self.args.scriptFiles:
                script_dir = os.path.dirname(script_path)
                script_name = os.path.basename(script_path)

                temp_script_path = os.path.join(temp_dir, script_name)

                storagecloud.download(
                    self.args.storageDelegate,
                    script_dir,
                    script_name,
                    self.args.storagePublicKey,
                    self.args.storagePrivateKey,
                    temp_script_path,
                    region_id=self.args.providerRegionId,
                    endpoint=self.args.storageEndpoint,
                    account=self.args.storageAccount)

                exe = self.conf.get_script_location(
                    "runConfigurationManagement-ENSTRATUS")
                cmd = [exe,
                       self.args.runAsUser,
                       str(self.conf.customer_id),
                       temp_script_path]
                (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
                if rc != 0:
                    raise exceptions.AgentPluginOperationException(
                        "Script %s failed" % script_name)
                t_stderr = t_stderr + stderr
                t_stdout = t_stdout + stdout
            return (t_stdout, t_stderr, 0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def run(self):
        if self.conf.is_imaging():
            raise exceptions.AgentPluginOperationIsImagingException(
                operation_name=self.name)

        _g_logger.info("Running configuration management of type " +
                       self.args.configType)

        if self.name == "configure_server" or\
                self.name == "configure_server_15":
            (stdout, stderr, rc) = self.configure_server_legacy()
        elif self.name == "configure_server_16":
            if self.args.configType.upper() != "ENSTRATUS":
                (stdout, stderr, rc) = self.configure_server_legacy()
            else:
                (stdout, stderr, rc) = self.configure_server_with_es()
        else:
            if self.args.configType.upper() == "ENSTRATUS":
                (stdout, stderr, rc) = self.configure_server_with_es()
            elif self.args.configType.upper() == "CHEF":
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
