import base64
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
import traceback
import uuid
import logging
import nose
from nose.plugins import skip
import time
import sys
import string

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


class CloudT(object):

    def __init__(self, id, key, secret, endpoint, account, region):
        self.id = id
        self.key = key
        self.secret = secret
        self.endpoint = endpoint
        self.account = account
        self.region = region

    def __str__(self):
        return "cloud_%d" % self.id


# does not inherit from unittest because of the python generators for
# testing storage clouds
class TestProtocolCommands(reply.ReplyObserverInterface):
    def new_message(self, reply):
        pass

    def message_done(self, reply):
        self._event.set()

    def incoming_message(self, incoming_doc):
        pass

    @classmethod
    def setUpClass(cls):
        test_utils.connect_to_debugger()
        cls.run_as_user = getpass.getuser()
        cls.test_base_path = tempfile.mkdtemp()
        conf_args = ["-c", "Amazon",
                     "-u", "http://doesntmatter.org/ws",
                     "-p", cls.test_base_path,
                     "-s", os.path.join(cls.test_base_path, "services"),
                     "-t", os.path.join(cls.test_base_path, "tmp"),
                     "-C", "success_tester",
                     "-U", cls.run_as_user,
                     "-l", "/tmp/agent_test_log.log"]
        rc = configure.main(conf_args)
        if rc != 0:
            raise Exception("We could not configure the test env")

    @classmethod
    def tearDownClass(cls):
        logger.clear_dcm_logging()

        shutil.rmtree(cls.test_base_path)

    def setUp(self):
        self.test_conf_path = \
            os.path.join(self.test_base_path, "etc", "agent.conf")
        self.conf_obj = config.AgentConfig([self.test_conf_path])
        self.svc = service.DCMAgent(self.conf_obj)

        self._event = threading.Event()

        utils.verify_config_file(self.conf_obj)
        # script_dir must be forced to None so that we get the built in dir
        self.svc.pre_threads()
        self.conf_obj.start_job_runner()

        self.disp = dispatcher.Dispatcher(self.conf_obj)
        self.test_con = test_conn.ReqRepQHolder()
        self.req_conn = self.test_con.get_req_conn()
        self.reply_conn = self.test_con.get_reply_conn()
        self.db = persistence.AgentDB(
            os.path.join(self.test_base_path, "etc", "agentdb.sql"))
        self.request_listener = reply.RequestListener(
            self.conf_obj, self.reply_conn, self.disp, self.db)
        observers = self.request_listener.get_reply_observers()
        observers.append(self)
        self.reply_conn.set_receiver(self.request_listener)

        self.agent_id = "theAgentID" + str(uuid.uuid4())
        self.customer_id = 50

        handshake_doc = {}
        handshake_doc["version"] = "1"
        handshake_doc["agentID"] = self.agent_id
        handshake_doc["cloudId"] = "Amazon"
        handshake_doc["customerId"] = self.customer_id
        handshake_doc["regionId"] = None
        handshake_doc["zoneId"] = "rack2"
        handshake_doc["serverId"] = "thisServer"
        handshake_doc["serverName"] = "dcm.testagent.com"
        handshake_doc["ephemeralFileSystem"] = "/tmp"
        handshake_doc["encryptedEphemeralFsKey"] = "DEADBEAF"

        self.svc.conn = self.reply_conn
        self.svc.disp = self.disp
        self.svc.request_listener = self.request_listener

        self.svc.incoming_handshake({"handshake": handshake_doc,
                                     "return_code": 200})

        self.disp.start_workers(self.request_listener)

    def _run_main_loop(self):
        self.svc.agent_main_loop()

    def _rpc_wait_reply(self, doc):

        class TestRequestReceiver(parent_receive_q.ParentReceiveQObserver):
            def __init__(self, req):
                self.req = req

            def incoming_parent_q_message(self, obj):
                self.req.incoming_message(obj)

        def reply_callback():
            parent_receive_q.wakeup()

        reqRPC = request.RequestRPC(doc, self.req_conn, self.agent_id,
                                    reply_callback=reply_callback)
        req_receiver = TestRequestReceiver(reqRPC)
        self.req_conn.set_receiver(req_receiver)

        reqRPC.send()

        # wait for message completion:
        while not self._event.isSet():
            parent_receive_q.poll()
        self._event.clear()

        reqRPC.cleanup()
        self.shutting_down = False

        return reqRPC

    def tearDown(self):
        print test_utils.build_assertion_exception("tester")
        self.request_listener.wait_for_all_nicely()
        self.svc.cleanup_agent()
        self.req_conn.close()
        test_utils.test_thread_shutdown()

    def test_get_private_ip(self):
        doc = {
            "command": "get_private_ip_address",
            "arguments": {"agent_token": None}
        }
        req_reply = self._rpc_wait_reply(doc)
        print req_reply.get_reply()
