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
from dcm.agent import utils
import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class RemoteTester(jobs.Plugin):

    protocol_arguments = {}

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RemoteTester, self).__init__(
            conf, job_id, items_map, name, arguments)

        self._port = int(items_map['remote_port'])
        self._host = items_map['remote_host']

        for i in range(3):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self._host, self._port))
                break
            except:
                if i == 2:
                    raise
        msg = {"name": name, "arguments": arguments}

        self._msg = json.dumps(msg)

    def run(self):
        try:
            utils.log_to_dcm(logging.INFO, "Test remote logging. %s"
                                           % str(self.arguments))
            _g_logger.info("Start tester remote socket.  Send " + self._msg)
            self.sock.send(self._msg)
            _g_logger.info("waiting to get a message back")

            msg = ""
            ch = ""
            while ch != '\n':
                ch = self.sock.recv(1)
                msg = msg + ch
            _g_logger.info("Tester plugin Received " + msg)
            self.sock.close()
            rc = json.loads(msg)
            return rc
        except Exception as ex:
            _g_logger.exception("Something went wrong here")
            return {'return_code': 1}
        except:
            _g_logger.exception("Something went wrong here")
            return {'return_code': 1}


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("IN TESTER LOAD")
    return RemoteTester(conf, job_id, items_map, name, arguments)
