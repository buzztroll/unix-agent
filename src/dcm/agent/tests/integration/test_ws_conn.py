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
import datetime
import getpass
import os
import socket
import unittest
import tempfile
import threading

import dcm.agent.cmd.configure as configure
import dcm.agent.cmd.service as service
import dcm.agent.config as config
import dcm.agent.tests.utils.general as test_utils


# does not inherit from unittest because of the python generators for
# testing storage clouds
class TestWsConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _write_conf(self):
        run_as_user = getpass.getuser()
        test_base_path = tempfile.mkdtemp()
        conf_args = ["-c", "Amazon",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", test_base_path,
                     "-C", "ws",
                     "-m", os.path.join(test_base_path, "mount"),
                     "-t", os.path.join(test_base_path, "tmp"),
                     "-U", run_as_user,
                     "-l", "/tmp/agent_test_log.log"]
        rc = configure.main(conf_args)
        if rc != 0:
            raise Exception("We could not configure the test env")
        return test_base_path

    def test_connection_backoff(self):
        test_base = self._write_conf()
        agent_conf_path = os.path.join(test_base, "etc", "agent.conf")
        conf = config.AgentConfig([agent_conf_path])
        conf.connection_max_backoff = 200
        conf.connection_backoff = 200
        test_run_time = 5000
        expected_connections = test_run_time / conf.connection_max_backoff

        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.listen(100)
        _, port = serversocket.getsockname()

        conf.connection_agentmanager_url = "ws://127.0.0.1:%d/ws" % port

        agent = service.DCMAgent(conf)
        conf.start_job_runner()

        def _run_agent(agent):
            agent.run_agent()

        t1 = threading.Thread(target=_run_agent, args=(agent,))
        t1.start()

        # run for time after the first connect.  that way we know it is up
        try:
            print("getting the first one")
            (clientsocket, address) = serversocket.accept()
            clientsocket.close()
            print("got it")
            connect_count = 0
            now = datetime.datetime.now()
            end_time = now + datetime.timedelta(seconds=test_run_time/1000)

            while now < end_time:
                print("waiting to connect " + str(now))
                (clientsocket, address) = serversocket.accept()
                clientsocket.close()
                connect_count += 1
                now = datetime.datetime.now()
                print("connected " + str(now))
        finally:
            serversocket.close()
            agent.shutdown_main_loop()
            t1.join()
        self.assertTrue(expected_connections * .9 - 1 < connect_count
                        < expected_connections * 1.1 + 1,
                        "connect_count is %d, expected %d" %
                        (connect_count, expected_connections))
