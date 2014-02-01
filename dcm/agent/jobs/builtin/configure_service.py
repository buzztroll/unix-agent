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

# TODO NOT DONE
#
#
# 	public JobDescription configureService(AgentToken token, long forCustomerId, String serviceId, String runAsUser,
# 			byte[] configurationData) throws AgentException, AgentSecurityException {
# 		logger.trace("enter - configureService");
# 		return configureServiceWithSSL(token, forCustomerId, serviceId, runAsUser, configurationData, null, null, null,
# 				null);
# 	}
#
# 	public JobDescription configureServiceWithSSL(AgentToken token, long forCustomerId, String serviceId,
# 			String runAsUser, byte[] configurationData, String address, String sslPublic, byte[] sslPrivate,
# 			String sslChain) throws AgentException, AgentSecurityException {
# 		logger.trace("enter - configureServiceWithSSL");
import logging
import os
from dcm.agent import exceptions, utils

import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class ConfigureService(jobs.Plugin):
    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ConfigureService, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.exe = conf.get_script_location(script_name)
        self._service_id = arguments["serviceId"]
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

            _g_logger.info("Writing SSL file: %s" % fname)
            with open(fname) as cert_f:
                try:
                    cert_f.write(data)
                except Exception as ex:
                    msg = "Could not write file: %s" % ex.message
                    _g_logger.error(msg)
                    raise exceptions.AgentJobException(msg)


    def _do_ssl(self, address, ssl_public, ssl_private, ssl_chain):
        if address is None or ssl_public is None or ssl_private is None:
            return

        # write out the SSL cert to service dir
        self._cert_file_name = os.path.join(self._conf.get_service_directory(),
                                            "cfg",
                                            self._service_id + ".cert")
        self._safe_write(self._cert_file_name, ssl_public)
        self._key_file_name = os.path.join(self._conf.get_service_directory(),
                                           "cfg",
                                           self._service_id + ".key")
        _g_logger.info("Writing SSL key: %s" % self._key_file_name)
        self._safe_write(self._key_file_name, ssl_private)

        if ssl_chain is not None:
            self._chain_file_name = os.path.join(
                self._conf.get_service_directory(), "cfg",
                self._service_id + ".chained")
            self._safe_write(self._chain_file_name, ssl_chain)

    def _delete_file(self, fname):
        if fname is None:
            return
        try:
            os.remove(fname)
        except OSError as osEx:
            _g_logger.debug("Failed to delete %s : %s" % (fname, osEx.message))

    def call(self):
        address = None
        try:
            address = self.arguments["address"]
            ssl_public = self.arguments["sslPublic"]
            ssl_private = self.arguments["sslPrivate"]
            ssl_chain = self.arguments["sslChain"]

            self._do_ssl(address, ssl_public, ssl_private, ssl_chain)

        except KeyError as ke:
            # if this happens it means we are not using ssl
            pass

        try:
            #Write out the temporary config file to the service directory...
            config_file_name = os.path.join(self._conf.get_service_directory(),
                                            "cfg",
                                            "enstratus.cfg")
            self._safe_write(config_file_name, self.arguments["configurationData"])

            cmd_list = [self.exe,
                        self.arguments["runAsUser"],
                        self.arguments["customerId"],
                        self._service_id]
            if address is not None and self._cert_file_name is not None and\
                    self._key_file_name is not None:
                cmd_list.append(address)
                cmd_list.append(self._cert_file_name)
                cmd_list.append(self._key_file_name)
                if self._chain_file_name is not None:
                    cmd_list.append(self._chain_file_name)

            (stdout, stderr, rc) = utils.run_command(cmd_list)
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
            # TODO clear out memory of secrets?


        reply_doc = {
            "return_code": 0,
            "reply_type": "agent_data",
            "reply_object": reply_object
        }
        return reply_doc


def load_plugin(conf, job_id, items_map, name, arguments):
    return ConfigureService(conf, job_id, items_map, name, arguments)
