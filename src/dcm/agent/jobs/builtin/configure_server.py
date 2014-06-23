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
        ("", True, str),
        "authId":
        ("", False, str),
        "configurationData":
        ("", False, utils.base64type_convertor),
        "encryptedConfigToken":
        ("", False, utils.base64type_convertor),
        "encryptedAuthSecret":
        ("", False, utils.base64type_convertor),
        "endpoint":
        ("", False, str),
        "providerRegionId":
        ("", False, str),
        "runAsUser":
        ("", False, str),
        "storageDelegate":
        ("", False, str),
        "storageEndpoint":
        ("", False, str),
        "storageAccount":
        ("", False, str),
        "scriptFiles":
        ("", False, list),
        "storagePublicKey":
        ("", False, utils.base64type_convertor),
        "storagePrivateKey":
        ("", False, utils.base64type_convertor),
        "environmentId":
        ("", False, str),
        "personalityFiles":
        ("", False, str),
        "configClientName":
        ("", False, str),
        "configCert":
        ("", False, utils.base64type_convertor),
        "runListIds":
        ("", False, str),
        "parameterList":
        ("", False, utils.base64type_convertor),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ConfigureServer, self).__init__(
            conf, job_id, items_map, name, arguments)
        if not self.args.runAsUser:
            self.args.runAsUser = \
                utils.make_id_string("c", self.conf.customer_id)

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
                   self.args.nodeName,
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
                       self.conf.customer_id,
                       temp_script_path]
                (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
                if rc != 0:
                    raise exceptions.AgentPluginOperationException(
                        "Script %s failed" % script_name)
                t_stderr = t_stderr + stderr
                t_stdout = t_stdout + stdout
            return (0, t_stdout, t_stderr)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def run(self):
        if self.conf.is_imaging():
            raise exceptions.AgentPluginOperationIsImagingException(
                operation_name=self.name)

        _g_logger.info("Running configuration management of type " +
                       self.args.configType)

        if self.args.runAsUser is None:
            self.args.runAsUser = self.conf.system_user

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
                (stdout, stderr, rc) = self.configure_server_legacy()

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
