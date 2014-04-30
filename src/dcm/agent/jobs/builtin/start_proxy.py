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
import socket
import dcm.agent.exceptions as exceptions
import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class StartProxy(jobs.Plugin):

    protocol_arguments = {
        "customerId":
        ("The ID of the customer invoking the command.", True, str),
        "serviceId":
        ("The ID of the service.", True, str),
        "onServiceIp":
        ("The ID of the service.", True, str),
        "atServicePort":
        ("The ID of the service.", True, int),
        "sslCert":
        ("The ID of the service.", True, str),
        "sslKey":
        ("The ID of the service.", True, str),
        "sslChain":
        ("The ID of the service.", True, str),
        "dnsNames":
        ("The ID of the service.", True, list)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(StartProxy, self).__init__(
            conf, job_id, items_map, name, arguments)

        script_name = items_map["script_name"]
        self.command = [conf.get_script_location(script_name),
                        arguments["serviceId"]]
        self.cwd = self.conf.get_service_directory(arguments["serviceId"])

    def run(self):
        if len(self.args.dnsNames) < 1:
            raise exceptions.AgentPluginParameterException(
                "At least one dns name must be sent to startProxy")

        primary_dns_name = self.args.dnsNames[0]
        if len(self.args.dnsNames) == 1:
            aliases = "NONE"
        else:
            aliases = ",".join(self.args.dnsNames[1:])

        self.ordered_param_list = [
            self.args.serviceId,
            primary_dns_name,
            aliases,
            socket.gethostbyname(socket.gethostname()),
            self.args.onServiceIp,
            str(self.args.atServicePort)]

        if self.args.sslCert and self.args.sslKey:
            self.ordered_param_list.append(self.args.sslCert)
            self.ordered_param_list.append(self.args.sslKey)

            try:
                cert_file_path = self.conf.get_temp_file(
                    self.args.serviceId + ".cert")
                with open(cert_file_path, "w") as fptr:
                    fptr.write(self.args.sslCert.decode("utf-8"))
                key_file_path = self.conf.get_temp_file(
                    self.args.serviceId + ".key")
                with open(key_file_path, "w") as fptr:
                    fptr.write(self.args.sslKey.decode("utf-8"))
                if self.args.sslChain:
                    self.ordered_param_list.append(self.args.sslChain)
                    chain_file_path = self.conf.get_temp_file(
                        self.args.serviceId + ".chained")
                    with open(chain_file_path, "w") as fptr:
                        fptr.write(self.args.sslChain.decode("utf-8"))
            except Exception as ex:
                _g_logger.exception("Failed to write credential files.")
                raise exceptions.AgentJobException(ex.message)

        return super(StartProxy, self).run()


def load_plugin(conf, job_id, items_map, name, arguments):
    return StartProxy(conf, job_id, items_map, name, arguments)
