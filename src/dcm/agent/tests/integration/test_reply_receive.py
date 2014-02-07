import random
import socket
import threading
import unittest
import pwd
from dcm.agent.cmd import service
from dcm.agent import config, dispatcher
from dcm.agent.messaging import reply, request
import dcm.agent.tests.utils as test_utils
import dcm.agent.tests.utils.test_connection as test_conn


class TestSimpleSingleCommands(unittest.TestCase):

    def setUp(self):
        service._g_shutting_down = False # this has to be the worst thing I have ever done

        self.conf_obj = config.AgentConfig()
        test_conf_path = test_utils.get_conf_file("agent.realplugins.conf")
        service._pre_threads(self.conf_obj, ["-c", test_conf_path])
        self.disp = dispatcher.Dispatcher(self.conf_obj)


        self.test_con = test_conn.ReqRepQHolder()
        self.req_conn = self.test_con.get_req_conn()
        self.reply_conn = self.test_con.get_reply_conn()

        self.request_listener = reply.RequestListener(
            self.conf_obj, self.reply_conn, self.disp)

        self.agent_id = "theAgentID"
        self.customer_id = 50

        handshake_doc = {}
        handshake_doc["version"] = "1"
        handshake_doc["agentID"] = self.agent_id
        handshake_doc["cloudId"] = "Amazon"
        handshake_doc["customerId"] = self.customer_id
        handshake_doc["regionId"] = "asia"
        handshake_doc["zoneId"] = "rack2"
        handshake_doc["serverId"] = "thisServer"
        handshake_doc["serverName"] = "dcm.testagent.com"
        handshake_doc["ephemeralFileSystem"] = "/tmp"
        handshake_doc["encryptedEphemeralFsKey"] = "DEADBEAF"

        self.conf_obj.set_handshake(handshake_doc)
        self.conf_obj.start_job_runner()

        self.thread = threading.Thread(target=self._run_main_loop)
        self.thread.start()
        self.disp.start_workers()

    def _run_main_loop(self):
        self.disp.stop()
        service._agent_main_loop(self.conf_obj,
                                 self.request_listener,
                                 self.disp,
                                 self.reply_conn)

    def _rpc_wait_reply(self, doc):

        x = []
        cond = threading.Condition()
        def reply_callback():
            cond.acquire()
            try:
                x.append(True)
                cond.notify_all()
            finally:
                cond.release()

        reqRPC = request.RequestRPC(doc, self.req_conn, self.agent_id,
                                    reply_callback=reply_callback)
        reqRPC.send()

        while not x:
            cond.acquire()
            try:
                msg = self.req_conn.recv()
                if msg != None:
                    reqRPC.incoming_message(msg)
                cond.wait(0.1)
            finally:
                cond.release()
            reqRPC.poll()

        reqRPC.cleanup()
        return reqRPC


    def tearDown(self):
        service.shutdown_main_loop()

    def test_get_private_ip(self):
        doc = {
            "command": "get_private_ip_address",
            "arguments": {"agent_token": None}
        }
        req_reply = self._rpc_wait_reply(doc)
        print req_reply.get_reply()
        # TODO verify that this matches the output of the command

    def test_heartbeat(self):
        doc = {
            "command": "heartbeat",
            "arguments": {}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()

        print r
        self.assertEquals(r["payload"]["reply_type"], "string")
        self.assertEquals(r["payload"]["return_code"], 0)

        # TODO verify that this matches the output of the command

    def test_get_agent_data(self):
        doc = {
            "command": "get_agent_data",
            "arguments": {"agent_token": None}
        }
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        self.assertEquals(r["payload"]["reply_type"], "agent_data")
        self.assertEquals(r["payload"]["return_code"], 0)


    def test_add_user_remove_user(self):
        user_name = "dcm" + str(random.randint(10, 99))

        doc = {
            "command": "add_user",
            "arguments": {"agent_token": None,
                          "customer_id": self.customer_id,
                          "user_id": user_name,
                          "password": None,
                          "first_name": "buzz",
                          "last_name": "troll",
                          "authentication": "public key data",
                          "administrator": False}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)

        pw_ent = pwd.getpwnam(user_name)

        self.assertEquals(pw_ent.pw_name, user_name)

        doc = {
            "command": "remove_user",
            "arguments": {"agent_token": None,
                          "user_id": user_name}}

        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertRaises(KeyError, pwd.getpwnam, user_name)

    def test_list_devices(self):
        doc = {
            "command": "list_devices",
            "arguments": {"agent_token": None}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        print r
        self.assertEquals(r["payload"]["return_code"], 0)

        # TODO verify that this matches the output of the command

    def test_get_service_states(self):
        doc = {
            "command": "get_service_states",
            "arguments": {"agent_token": None}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        print r
        self.assertEquals(r["payload"]["return_code"], 0)

        # TODO verify that this matches the output of the command

    def test_rename(self):
        orig_hostname = socket.gethostname()

        new_hostname = "buzztroll.net"
        doc = {
            "command": "rename",
            "arguments": {"agent_token": None, "server_name": new_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)

        self.assertEqual(socket.gethostname(), new_hostname)

        doc = {
            "command": "rename",
            "arguments": {"agent_token": None, "server_name": orig_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)

        self.assertEqual(socket.gethostname(), orig_hostname)

    # def test_start_service(self):
    #     doc = {
    #         "command": "start_service",
    #         "arguments": {"agent_token": None,
    #                       "customer_id": self.customer_id,
    #                       "service_id": }
    #     }
    #     req_reply = self._rpc_wait_reply(doc)
    #     r = req_reply.get_reply()
    #     print r
    #     # TODO verify that this matches the output of the command
