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

import logging
import os
from dcm.agent import exceptions, utils

import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


# This handlers configure_service_with_ssl and configure_service
class ConfigureService(jobs.Plugin):

    protocol_arguments = {
        "forCustomerId":
            ("The ID of the customer running the configuration.",
             True, str),
        "serviceId":
            ("The ID of the service on which enstratus-configure will be run.",
             True, str),
        "runAsUser":
            ("The unix account name that will run the configuration.",
             True, str),
        "configurationData":
            ("Data that will be written to a file and passed to the script "
             "enstratus-configure as configuration data",
             True, str),
        "addressForSSL":
            ("The ssl address.",
             False, str),
        "sslPublic":
            ("The SSL public key.", False, str),
        "sslPrivate":
            ("The SSL private key.", False, str),
        "sslChain":
            ("The SSL CA chain.", False, str),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ConfigureService, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.exe = conf.get_script_location(script_name)

        self._customer_id = arguments["forCustomerId"]
        self._service_id = arguments["serviceId"]
        self._run_as_user = arguments["runAsUser"]
        self._configuration_data = arguments["configurationData"]

        # with ssl parameters
        self._address = arguments.get("address", None)
        self._ssl_public = arguments.get("sslPublic", None)
        self._ssl_private = arguments.get("sslPrivate", None)
        self._ssl_chain = arguments.get("sslChain", None)

        self._cert_file_name = None
        self._key_file_name = None
        self._chain_file_name = None

    def _safe_write(self, fname, data):
        if os.path.exists(fname):
            try:
                os.remove(fname)
            except OSError:
                msg = "Could not overwrite existing SSL file."
                _g_logger.error(msg)
                raise exceptions.AgentJobException(msg)

        _g_logger.info("Writing file: %s" % fname)
        with open(fname, "w") as cert_f:
            try:
                cert_f.write(data)
            except Exception as ex:
                msg = "Could not write file: %s" % ex.message
                _g_logger.error(msg)
                raise exceptions.AgentJobException(msg)

    def _do_ssl(self):
        # write out the SSL cert to service dir
        self._cert_file_name = os.path.join(
            self.conf.get_service_directory(self._service_id),
            "cfg",
            self._service_id + ".cert")
        self._safe_write(self._cert_file_name, self._ssl_public)
        self._key_file_name = os.path.join(
            self.conf.get_service_directory(self._service_id),
            "cfg",
            self._service_id + ".key")
        _g_logger.info("Writing SSL key: %s" % self._key_file_name)
        self._safe_write(self._key_file_name, self._ssl_private)

        if self._ssl_chain is not None:
            self._chain_file_name = os.path.join(
                self.conf.get_service_directory(self._service_id), "cfg",
                self._service_id + ".chained")
            self._safe_write(self._chain_file_name, self._ssl_chain)

    def _delete_file(self, fname):
        if fname is None:
            return
        try:
            os.remove(fname)
        except OSError as osEx:
            _g_logger.debug("Failed to delete %s : %s" % (fname, osEx.message))

    def run(self):
        if self._address is not None and self._ssl_public is not None\
            and self._ssl_private is not None:
            self._do_ssl()

        try:
            #Write out the temporary config file to the service directory...
            config_file_name = os.path.join(
                self.conf.get_service_directory(self._service_id),
                "cfg",
                "enstratiusinitd.cfg")
            self._safe_write(config_file_name, self._configuration_data)

            cmd_list = [self.exe,
                        self._run_as_user,
                        self._customer_id,
                        self._service_id]
            if self._address is not None and self._cert_file_name is not None\
                    and self._key_file_name is not None:
                cmd_list.append(self._address)
                cmd_list.append(self._cert_file_name)
                cmd_list.append(self._key_file_name)
                if self._chain_file_name is not None:
                    cmd_list.append(self._chain_file_name)

            (stdout, stderr, rc) = utils.run_command(self.conf, cmd_list)
            if rc != 0:
                reply_doc = {"return_code": rc,
                             "message": stderr}
            else:
                reply_doc = {"return_code": rc,
                             "reply_type": "string",
                             "reply_object": stdout}
            return reply_doc
        finally:
            self._delete_file(self._cert_file_name)
            self._delete_file(self._key_file_name)
            self._delete_file(self._chain_file_name)


def load_plugin(conf, job_id, items_map, name, arguments):
    return ConfigureService(conf, job_id, items_map, name, arguments)
