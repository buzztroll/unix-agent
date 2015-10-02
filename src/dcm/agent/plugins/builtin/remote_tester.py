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
            rc_dict = json.loads(in_msg.decode())
            rc = rc_dict['return_code']
            try:
                reply_type = rc_dict['reply_type']
            except KeyError:
                reply_type = None
            try:
                reply_object = rc_dict['reply_object']
            except KeyError:
                reply_object = None
            try:
                message = rc_dict['message']
            except KeyError:
                message = None
            try:
                error_message = rc_dict['error_message']
            except KeyError:
                error_message = None

            rc = plugin_base.PluginReply(rc,
                                         reply_type=reply_type,
                                         reply_object=reply_object,
                                         message=message,
                                         error_message=error_message)
            _g_logger.info("Tester plugin sending back " + str(rc))
            return rc
        except:
            _g_logger.exception("Something went wrong here")
            return plugin_base.PluginReply(1)


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("IN TESTER LOAD")
    return RemoteTester(conf, job_id, items_map, name, arguments)
