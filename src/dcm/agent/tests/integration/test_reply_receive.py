import os
import random
import shutil
import socket
import unittest
import pwd
import datetime
import uuid
from dcm.agent.cmd import service
from dcm.agent import config, dispatcher, storagecloud, parent_receive_q
from dcm.agent.messaging import reply, request
import dcm.agent.tests.utils as test_utils
import dcm.agent.tests.utils.test_connection as test_conn


class TestSimpleSingleCommands(unittest.TestCase):

    def setUp(self):
        service._g_shutting_down = False # this has to be the worst thing I have ever done
        service._g_conn_for_shutdown = None # and this

        test_conf_path = test_utils.get_conf_file("agent.realplugins.conf")
        self.conf_obj = config.AgentConfig([test_conf_path])
        # script_dir must be forced to None so that we get the built in dir
        self.conf_obj.storage_script_dir = None
        service._pre_threads(self.conf_obj, ["-c", test_conf_path])
        self.disp = dispatcher.Dispatcher(self.conf_obj)

        self.test_con = test_conn.ReqRepQHolder()

        self.req_conn = self.test_con.get_req_conn()
        self.reply_conn = self.test_con.get_reply_conn()

        self.request_listener = reply.RequestListener(
            self.conf_obj, self.reply_conn, self.disp)
        self.reply_conn.set_receiver(self.request_listener)

        self.agent_id = "theAgentID" + str(uuid.uuid4())
        self.customer_id = 50

        handshake_doc = {}
        handshake_doc["version"] = "1"
        handshake_doc["agentID"] = self.agent_id
        handshake_doc["cloudId"] = "Amazon"
        handshake_doc["customerId"] = self.customer_id
        handshake_doc["regionId"] = "us_west_oregon"
        handshake_doc["zoneId"] = "rack2"
        handshake_doc["serverId"] = "thisServer"
        handshake_doc["serverName"] = "dcm.testagent.com"
        handshake_doc["ephemeralFileSystem"] = "/tmp"
        handshake_doc["encryptedEphemeralFsKey"] = "DEADBEAF"

        self.conf_obj.set_handshake(handshake_doc)
        self.conf_obj.start_job_runner()

        self.disp.start_workers(self.request_listener)

    def _run_main_loop(self):
        service._agent_main_loop(self.conf_obj,
                                 self.request_listener,
                                 self.disp,
                                 self.reply_conn)

    def _rpc_wait_reply(self, doc):

        class TestRequestReceiver(parent_receive_q.ParentReceiveQObserver):
            def __init__(self, req):
                self.req = req

            def incoming_parent_q_message(self, obj):
                self.req.incoming_message(obj)

        def reply_callback():
            service.shutdown_main_loop()

        reqRPC = request.RequestRPC(doc, self.req_conn, self.agent_id,
                                    reply_callback=reply_callback)
        req_receiver = TestRequestReceiver(reqRPC)
        self.req_conn.set_receiver(req_receiver)

        reqRPC.send()

        self._run_main_loop()

        reqRPC.cleanup()

        return reqRPC

    def tearDown(self):
        self.request_listener.wait_for_all_nicely()
        service._cleanup_agent(
            self.conf_obj, self.request_listener, self.disp, self.reply_conn)
        self.req_conn.close()

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

    @test_utils.system_changing
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
        self.assertEquals(r["payload"]["return_code"], 0)

        # TODO verify that this matches the output of the command

    def test_get_service_states(self):
        doc = {
            "command": "get_service_states",
            "arguments": {"agent_token": None}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)

        # TODO verify that this matches the output of the command

    @test_utils.system_changing
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

    def _get_job_description(self, job_id):
        arguments = {
            "agent_token": None,
            "jobId": job_id
        }
        doc = {
            "command": "get_job_description",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertEquals(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]

        return jd


    @test_utils.system_changing
    def test_install_start_stop_configure_service(self):
        """
        install a service, start it, configure it in two ways, stop it, then
        delete the directory it was put into
        """
        service_id = "asuccess_service"

        # test install
        arguments = {
            "agent_token": None,
            "customerId": self.customer_id,
            "serviceId": service_id,
            "fromCloudId": 1,
            "runAsUser": "vagrant",
            "storageAccessKey": os.environ["S3_ACCESS_KEY"],
            "storageSecretKey": os.environ["S3_SECRET_KEY"],
            "encryption": "not_used",
            "encryptionPublicKey": "not_used",
            "encryptionPrivateKey": "not_user",
            "serviceImageDirectory": "enstratiustests",
            "serviceImageFile": "success_service.tar.gz"
        }

        doc = {
            "command": "install_service",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertEquals(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        self.assertEqual(jd["job_status"], "COMPLETE")

        service_dir = self.conf_obj.get_service_directory(service_id)
        self.assertTrue(os.path.exists(service_dir))
        self.assertTrue(os.path.exists(
            os.path.join(service_dir, "bin/enstratiusinitd-configure")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratiusinitd-stop")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratiusinitd-start")))

        # test start
        arguments = {
            "agent_token": None,
            "customerId": self.customer_id,
            "serviceId": service_id
        }
        doc = {
            "command": "start_service",
            "arguments": arguments
        }
        start_time = datetime.datetime.now()
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertTrue(os.path.exists("/tmp/service_start"))

        with open("/tmp/service_start", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm > start_time)

        configuration_data = """
        This is some configuration data.
        That will be writen over there
        """

        # test configure
        arguments = {
            "agent_token": None,
            "forCustomerId": self.customer_id,
            "serviceId": service_id,
            "runAsUser": "vagrant",
            "configurationData": configuration_data
        }
        doc = {
            "command": "configure_service",
            "arguments": arguments
        }
        start_time = datetime.datetime.now()
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        self.assertEqual(jd["job_status"], "COMPLETE")

        self.assertTrue(os.path.exists("/tmp/service_configure"))

        with open("/tmp/service_configure", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm > start_time)

        cfg_file = os.path.join(service_dir, "cfg", "enstratiusinitd.cfg")
        self.assertTrue(os.path.exists(cfg_file))

        with open(cfg_file, "r") as fptr:
            data = fptr.read()
            self.assertEqual(data, configuration_data)

        ssl_public = "SFSOHWEKJRNMNSD<MNCSDNFSLEJFLKSENF<SDNCVDMS< CV"
        ssl_private = "sdfsdfsdjkhwekrjnwekrnweknv,mx vm,nwekrnlwekndfems,nfsd"
        configuration_data = configuration_data + "poerPPPO"

        # test with ssl configure
        arguments = {
            "agent_token": None,
            "forCustomerId": self.customer_id,
            "serviceId": service_id,
            "runAsUser": "vagrant",
            "configurationData": configuration_data,

            "address": "http://someplacefcdx.com",
            "sslPublic": ssl_public,
            "sslPrivate": ssl_private,
            "sslChain": None
        }
        doc = {
            "command": "configure_service_with_ssl",
            "arguments": arguments
        }
        start_time = datetime.datetime.now()
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        self.assertEqual(jd["job_status"], "COMPLETE")

        self.assertTrue(os.path.exists("/tmp/service_configure"))

        with open("/tmp/service_configure", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm > start_time)

        cfg_file = os.path.join(service_dir, "cfg", "enstratiusinitd.cfg")
        self.assertTrue(os.path.exists(cfg_file))

        with open(cfg_file, "r") as fptr:
            data = fptr.read()
            self.assertEqual(data, configuration_data)

        # get service state
        arguments = {
            "agent_token": None
        }
        doc = {
            "command": "get_service_states",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertEquals(r["payload"]["reply_type"], "string_array")
        service_array = r["payload"]["reply_object"]

        self.assertEqual([service_id, 'OK'], service_array)

        # install data source
        arguments = {
            "agent_token": None,
            "customerId": self.customer_id,
            "serviceId": service_id,
            "fromCloudId": 1,
            "runAsUser": "vagrant",
            "storageAccessKey": os.environ["S3_ACCESS_KEY"],
            "storageSecretKey": os.environ["S3_SECRET_KEY"],
            "configuration": configuration_data,
            "imageDirectory": "enstratiustests",
            "dataSourceImage": "success_service.tar.gz"
        }
        doc = {
            "command": "install_data_source",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertEquals(r["payload"]["reply_type"], "job_description")
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        self.assertEqual(jd["job_status"], "COMPLETE")

        # test stop
        arguments = {
            "agent_token": None,
            "customerId": self.customer_id,
            "serviceId": service_id
        }
        doc = {
            "command": "stop_service",
            "arguments": arguments
        }
        start_time = datetime.datetime.now()
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertTrue(os.path.exists("/tmp/service_stop"))

        with open("/tmp/service_stop", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm > start_time)
        shutil.rmtree(service_dir)

    @test_utils.system_changing
    def test_install_backup_data_set_service(self):
        """
        install a service, start it, configure it in two ways, stop it, then
        delete the directory it was put into
        """
        service_id = "asuccess_service"

        nw = datetime.datetime.now()
        tm_str = nw.strftime("%Y%m%d%H%M%S")
        container_name = "enstratiustests"
        dataSourceName = "somename%d" % random.randint(0, 1000) + tm_str

        # test install
        arguments = {
            "agent_token": None,
            "customerId": self.customer_id,
            "serviceId": service_id,
            "fromCloudId": 1,
            "runAsUser": "vagrant",
            "storageAccessKey": os.environ["S3_ACCESS_KEY"],
            "storageSecretKey": os.environ["S3_SECRET_KEY"],
            "encryption": "not_used",
            "encryptionPublicKey": "not_used",
            "encryptionPrivateKey": "not_user",
            "serviceImageDirectory": container_name,
            "serviceImageFile": "success_service.tar.gz"
        }

        doc = {
            "command": "install_service",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertEquals(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        self.assertEqual(jd["job_status"], "COMPLETE")

        service_dir = self.conf_obj.get_service_directory(service_id)
        self.assertTrue(os.path.exists(service_dir))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratiusinitd-configure")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratiusinitd-stop")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratiusinitd-start")))

        configuration_data = """
        This is some configuration data.
        That will be writen over there
        """

         # test install
        arguments = {
            "agent_token": None,
            "configuration": configuration_data,
            "customerId": self.customer_id,
            "serviceId": service_id,
            "inCloudId": 1,
            "runAsUser": "vagrant",
            "cloudAccessKey": os.environ["S3_ACCESS_KEY"],
            "cloudSecretKey": os.environ["S3_SECRET_KEY"],
            "encryption": "not_used",
            "encryptionPublicKey": "not_used",
            "encryptionPrivateKey": "not_used",
            "toBackupDirectory": "enstratiustests",
            "serviceImageFile": "success_service.tar.gz",
            "providerRegionId": "us_west_oregon",
            "dataSourceName": dataSourceName
        }
        doc = {
            "command": "backup_data_source",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertEquals(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        self.assertEqual(jd["job_status"], "COMPLETE")
        shutil.rmtree(service_dir)

        cloud = storagecloud.get_cloud_driver(
            arguments["inCloudId"],
            arguments["cloudAccessKey"],
            arguments["cloudSecretKey"],
            region_id=arguments["providerRegionId"])

        container = cloud.get_container(arguments["toBackupDirectory"])
        obj_list = cloud.list_container_objects(container)

        found = False
        for o in obj_list:
            ndx = o.name.find(dataSourceName)
            if ndx >= 0:
                found = True
                cloud.delete_object(o)

        self.assertTrue(found)
