import base64
from collections import namedtuple
import getpass
import hashlib
import os
import random
import re
import shutil
import socket
import tarfile
import tempfile
import threading
import pwd
import datetime
import uuid
import logging
import nose
from nose.plugins import skip
import time

import dcm.agent
import dcm.agent.utils as utils
from dcm.agent.cmd import service, configure
import dcm.agent.storagecloud as storagecloud
import dcm.agent.parent_receive_q as parent_receive_q
import dcm.agent.logger as logger
import dcm.agent.dispatcher as dispatcher
import dcm.agent.config as config
from dcm.agent.messaging import reply, request, persistence
import dcm.agent.tests.utils as test_utils
import dcm.agent.tests.utils.test_connection as test_conn


# does not inherit from unittest because of the python generators for
# testing storage clouds
class TestWsConnection(object):

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
                     "-P", "ubuntu",
                     "-C", "ws",
                     "-m", os.path.join(test_base_path, "mount"),
                     "-s", os.path.join(test_base_path, "services"),
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
        conf.connection_max_backoff = 100
        conf.connection_backoff = 100
        test_run_time = 5000

        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.listen(10)
        _, port = serversocket.getsockname()

        conf.connection_agentmanager_url = "ws://127.0.0.1:%d/ws" % port

        agent = service.DCMAgent(conf)
        conf.start_job_runner()

        def _run_agent(agent):
            agent.run_agent()

        t1 = threading.Thread(target=_run_agent, args=(agent,))
        t1.start()

        now = datetime.datetime.now()
        end_time = now + datetime.timedelta(seconds=test_run_time/1000)

        connect_count = 0

        while now < end_time:
            (clientsocket, address) = serversocket.accept()
            clientsocket.close()
            connect_count += 1
            now = datetime.datetime.now()
        agent.shutdown_main_loop()
        t1.join()

        nose.tools.ok_(10 < connect_count < 50)
