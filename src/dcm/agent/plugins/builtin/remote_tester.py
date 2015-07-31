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
import socket

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.logger as dcm_logger


_g_logger = logging.getLogger(__name__)


class RemoteTester(plugin_base.Plugin):

    protocol_arguments = {}

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RemoteTester, self).__init__(
            conf, job_id, items_map, name, arguments)

        self._port = int(items_map['remote_port'])
        self._host = items_map['remote_host']

    def run(self):
        try:
            dcm_logger.log_to_dcm_console_job_details(
                job_name=self.name,
                details="Test remote logging. %s" % str(self.arguments))
            for i in range(3):
                try:
                    self.sock = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
                    self.sock.connect((self._host, self._port))
                    break
                except:
                    if i == 2:
                        raise

            msg = {"name": self.name, "arguments": self.arguments}

            self._msg = json.dumps(msg)

            _g_logger.info("Start tester remote socket.  Send " + self._msg)
            self.sock.send(self._msg.encode())
            _g_logger.info("waiting to get a message back")

            in_msg = b''
            ch = b'123'
            while len(ch) > 0:
                ch = self.sock.recv(1024)
                in_msg = in_msg + ch
            _g_logger.info("Tester plugin Received " + in_msg.decode())
            self.sock.close()
            rc = json.loads(in_msg.decode())
            _g_logger.info("Tester plugin sending back " + str(rc))
            return rc
        except Exception:
            _g_logger.exception("Something went wrong here")
            return {'return_code': 1}
        except:
            _g_logger.exception("Something went wrong here")
            return {'return_code': 1}


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("IN TESTER LOAD")
    return RemoteTester(conf, job_id, items_map, name, arguments)
