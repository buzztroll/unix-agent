import getpass
import os
import random
import re
import shutil
import socket
import tarfile
import tempfile
import threading
import unittest
import pwd
import datetime
import uuid
from libcloud.common.types import LibcloudError

import dcm.agent.utils as utils
from dcm.agent.cmd import service, configure
from dcm.agent import config, dispatcher, storagecloud, parent_receive_q
from dcm.agent.messaging import reply, request
import dcm.agent.tests.utils as test_utils
import dcm.agent.tests.utils.test_connection as test_conn


class TestProtocolCommands(unittest.TestCase, reply.ReplyObserverInterface):

    def new_message(self, reply):
        pass

    def message_done(self, reply):
        self._event.set()

    def incoming_message(self, incoming_doc):
        pass

    @classmethod
    def _setup_s3(cls):
        cls.backup_bucket = "enstartiustestonetwo" + str(uuid.uuid4()).split("-")[0]
        cls.backup_bucket2 = "enstartiustesttwotwo"+ str(uuid.uuid4()).split("-")[0]
        cls.default_s3_region = "us_west_oregon"
        cls.default_s3_region2 = "us_west"
        cls.simple_service = "asimple_service.tar.gz"

        if "S3_SECRET_KEY" not in os.environ or "S3_ACCESS_KEY" not in os.environ:
            return

        etc_dir = os.path.dirname(os.path.dirname(__file__))
        tar_dir = tempfile.mkdtemp()
        tar_path = os.path.join(tar_dir, cls.simple_service)
        with tarfile.open(tar_path, "w:gz") as tar:
            for fname in os.listdir(os.path.join(etc_dir, "etc", "simple_service")):
                tar.add(os.path.join(etc_dir, "etc", "simple_service", fname), arcname=fname)

        check_list = [(cls.default_s3_region, cls.backup_bucket),
                      (cls.default_s3_region2, cls.backup_bucket2)]
        for region, bucket_name in check_list:
            cloud = storagecloud.get_cloud_driver(
                1,
                os.environ["S3_ACCESS_KEY"],
                os.environ["S3_SECRET_KEY"],
                    region_id=region)
            try:
                cloud.create_container(bucket_name)
            except LibcloudError as ex:
                pass

            container = cloud.get_container(bucket_name)
            cloud.upload_object(tar_path, container, cls.simple_service)

        shutil.rmtree(tar_dir)

    @classmethod
    def setUpClass(cls):
        PYDEVD_CONTACT = "PYDEVD_CONTACT"
        if PYDEVD_CONTACT in os.environ:
            pydev_contact = os.environ[PYDEVD_CONTACT]
            host, port = pydev_contact.split(":", 1)
            utils.setup_remote_pydev(host, int(port))
        # create the config file and other needed dirs

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
        try:
            cls._setup_s3()
        except Exception as ex:
            pass

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_base_path)
        if "S3_SECRET_KEY" not in os.environ or "S3_ACCESS_KEY" not in os.environ:
            return
        check_list = [(cls.default_s3_region, cls.backup_bucket),
                      (cls.default_s3_region2, cls.backup_bucket2)]
        for region, bucket_name in check_list:
            cloud = storagecloud.get_cloud_driver(
                1,
                os.environ["S3_ACCESS_KEY"],
                os.environ["S3_SECRET_KEY"],
                region_id=region)

            try:
                container = cloud.get_container(bucket_name)
                obj_list = cloud.list_container_objects(container)
                for o in obj_list:
                    cloud.delete_object(o)
                cloud.delete_container(container)
            except:
                pass

    def setUp(self):
        service._g_conn_for_shutdown = None # and this

        self._event = threading.Event()

        test_conf_path = os.path.join(self.test_base_path, "etc", "agent.conf")
        self.conf_obj = config.AgentConfig([test_conf_path])
        # script_dir must be forced to None so that we get the built in dir
        service._pre_threads(self.conf_obj, ["-c", test_conf_path])
        self.disp = dispatcher.Dispatcher(self.conf_obj)

        self.test_con = test_conn.ReqRepQHolder()

        self.req_conn = self.test_con.get_req_conn()
        self.reply_conn = self.test_con.get_reply_conn()

        self.request_listener = reply.RequestListener(
            self.conf_obj, self.reply_conn, self.disp)
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
        handshake_doc["regionId"] = self.default_s3_region
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
            service._g_shutting_down = True
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
        service._g_shutting_down = False

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
            "arguments": {"customerId": self.customer_id,
                          "userId": user_name,
                          "password": None,
                          "firstName": "buzz",
                          "lastName": "troll",
                          "authentication": "public key data",
                          "administrator": False}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)

        pw_ent = pwd.getpwnam(user_name)

        self.assertEquals(pw_ent.pw_name, user_name)

        doc = {
            "command": "remove_user",
            "arguments": {"userId": user_name}}

        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertRaises(KeyError, pwd.getpwnam, user_name)

    @test_utils.system_changing
    def test_initialize(self):
        cust = 10l
        orig_hostname = socket.gethostname()
        new_hostname = "testdcmagent"
        doc = {
            "command": "initialize",
            "arguments": {"cloudId": "3",
                          "customerId": cust,
                          "regionId": None,
                          "zoneId": None,
                          "serverId": self.agent_id,
                          "serverName": new_hostname,
                          "encryptedEphemeralFsKey": None}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertEquals(socket.gethostname(), new_hostname)

        customer_user = utils.make_id_string("c", cust)
        pw_ent = pwd.getpwnam(customer_user)
        self.assertEquals(pw_ent.pw_name, customer_user)

    def test_list_devices(self):
        doc = {
            "command": "list_devices",
            "arguments": {}
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
            "arguments": {"serverName": new_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)

        self.assertEqual(socket.gethostname(), new_hostname)

        doc = {
            "command": "rename",
            "arguments": {"serverName": orig_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)

        self.assertEqual(socket.gethostname(), orig_hostname)

    def _get_job_description(self, job_id):
        arguments = {
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

    def _install_service(self, service_id, bucket, fname, other_storage=False):
        # test install
        arguments = {
            "customerId": self.customer_id,
            "serviceId": service_id,
            "cloudId": 1,
            "runAsUser": self.run_as_user,
            "apiAccessKey": os.environ["S3_ACCESS_KEY"],
            "apiSecretKey": os.environ["S3_SECRET_KEY"],
            "serviceImageDirectory": bucket,
            "serviceImageFile": fname
        }
        if other_storage:
            arguments["storageAccessKey"] = os.environ["S3_ACCESS_KEY"]
            arguments["storageSecretKey"] = os.environ["S3_SECRET_KEY"]
            arguments["storageDelegate"] = 1

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
            os.path.join(service_dir, "bin/enstratus-configure")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-stop")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-start")))

    @test_utils.system_changing
    @test_utils.s3_needed
    def test_alt_service_install(self):
        service_id = "asuccess_service_two"
        self._install_service(service_id, self.backup_bucket,
                              self.simple_service, other_storage=True)

    @test_utils.system_changing
    @test_utils.s3_needed
    def test_install_start_stop_configure_service(self):
        """
        install a service, start it, configure it in two ways, stop it, then
        delete the directory it was put into
        """
        service_id = "asuccess_service"
        self._install_service(service_id,
                              self.backup_bucket,
                              self.simple_service)

        service_dir = self.conf_obj.get_service_directory(service_id)
        self.assertTrue(os.path.exists(service_dir))
        self.assertTrue(os.path.exists(
            os.path.join(service_dir, "bin/enstratus-configure")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-stop")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-start")))

        # test start
        arguments = {
            "customerId": self.customer_id,
            "serviceId": service_id
        }
        doc = {
            "command": "start_service",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertTrue(os.path.exists("/tmp/service_start"))

        with open("/tmp/service_start", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm >= start_time)

        configuration_data = """
        This is some configuration data.
        That will be writen over there
        """

        # test configure
        arguments = {
            "forCustomerId": self.customer_id,
            "serviceId": service_id,
            "runAsUser": self.run_as_user,
            "configurationData": configuration_data
        }
        doc = {
            "command": "configure_service",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
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
            params = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm >= start_time)
        p_a = params.split()
        self.assertEqual(len(p_a), 2)

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
            "forCustomerId": self.customer_id,
            "serviceId": service_id,
            "runAsUser": self.run_as_user,
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
        start_time = datetime.datetime.now().replace(microsecond=0)
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
            params = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm >= start_time)
        p_a = params.split()
        self.assertEqual(len(p_a), 5)

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

        self.assertIn(service_id, service_array)
        self.assertEqual(service_array[service_array.index(service_id) + 1],
                         'OK')

        # install data source
        arguments = {
            "customerId": self.customer_id,
            "serviceId": service_id,
            "cloudId": 1,
            "runAsUser": self.run_as_user,
            "apiAccessKey": os.environ["S3_ACCESS_KEY"],
            "apiSecretKey": os.environ["S3_SECRET_KEY"],
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
            "customerId": self.customer_id,
            "serviceId": service_id
        }
        doc = {
            "command": "stop_service",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertTrue(os.path.exists("/tmp/service_stop"))

        with open("/tmp/service_stop", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm >= start_time)
        shutil.rmtree(service_dir)

    def _backup_data(self,
                     s_id,
                     file_path,
                     use_storage=False,
                     use_offsite=False):

        object_name = "objname" + str(uuid.uuid4()).split("-")[0]
        cfg = """
        A bunch of config data
        """ + str(uuid.uuid4())

        check_list = [(self.default_s3_region, self.backup_bucket)]

        arguments = {
            "configuration": cfg,
            "serviceId": s_id,
            "primaryCloudId": 1,
            "runAsUser": self.run_as_user,
            "primaryApiKey": os.environ["S3_ACCESS_KEY"],
            "primarySecretKey": os.environ["S3_SECRET_KEY"],
            "toBackupDirectory": self.backup_bucket,
            "serviceImageFile": file_path,
            "dataSourceName": object_name,
            "primaryRegionId": self.default_s3_region
        }
        if use_storage:
            arguments["storageDelegate"] = 1
            arguments["storageApiKey"] = os.environ["S3_ACCESS_KEY"]
            arguments["storageSecretKey"]= os.environ["S3_SECRET_KEY"]

        if use_offsite:
            check_list.append((self.default_s3_region2, self.backup_bucket2))
            arguments["secondaryCloudId"] = 1
            arguments["secondaryApiKey"] = os.environ["S3_ACCESS_KEY"]
            arguments["secondarySecretKey"]= os.environ["S3_SECRET_KEY"]
            arguments["secondaryRegionId"]= self.default_s3_region2
            if use_storage:
                arguments["secondaryStorageDelegate"] = 1
                arguments["secondaryStorageApiKey"] = os.environ["S3_ACCESS_KEY"]
                arguments["secondaryStorageSecretKey"]= os.environ["S3_SECRET_KEY"]

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

        for region, bucket in check_list:
            cloud = storagecloud.get_cloud_driver(
                1,
                os.environ["S3_ACCESS_KEY"],
                os.environ["S3_SECRET_KEY"],
                region_id=region)

            found = False
            container = cloud.get_container(bucket)
            obj_list = cloud.list_container_objects(container)
            for obj in obj_list:
                ndx = obj.name.find(object_name)
                if ndx >= 0:
                    found = True
            self.assertTrue(found)

    @test_utils.s3_needed
    def test_backup_data_just_one(self):
        service_id = "aservice_for_backup" + str(uuid.uuid4())
        self._install_service(service_id,
                              self.backup_bucket,
                              self.simple_service)

        service_dir = self.conf_obj.get_service_directory(service_id)
        self.assertTrue(os.path.exists(service_dir))
        self.assertTrue(os.path.exists(
            os.path.join(service_dir, "bin/enstratus-dbgrant")))

        self._backup_data(service_id, service_id + ".tar.gz")

    @test_utils.s3_needed
    def test_backup_data_just_one_storage(self):
        service_id = "aservice_for_backup_store" + str(uuid.uuid4())
        self._install_service(service_id,
                              self.backup_bucket,
                              self.simple_service)

        service_dir = self.conf_obj.get_service_directory(service_id)
        self.assertTrue(os.path.exists(service_dir))
        self.assertTrue(os.path.exists(
            os.path.join(service_dir, "bin/enstratus-dbgrant")))

        self._backup_data(service_id, service_id + ".tar.gz", use_storage=True)

    # offsite will not work with S3 because the bucket names are the same
    # @test_utils.s3_needed
    # def test_backup_data_offsite(self):
    #     service_id = "aservice_for_twobackup" + str(uuid.uuid4())
    #     self._install_service(service_id,
    #                           self.backup_bucket,
    #                           self.simple_service)
    #
    #     service_dir = self.conf_obj.get_service_directory(service_id)
    #     self.assertTrue(os.path.exists(service_dir))
    #     self.assertTrue(os.path.exists(
    #         os.path.join(service_dir, "bin/enstratus-dbgrant")))
    #
    #     self._backup_data(service_id, service_id + ".tar.gz", use_offsite=True)
    #
    # @test_utils.s3_needed
    # def test_backup_data_offsite_storage(self):
    #     service_id = "aservice_for_twobackup_storage" + str(uuid.uuid4())
    #     self._install_service(service_id,
    #                           self.backup_bucket,
    #                           self.simple_service)
    #
    #     service_dir = self.conf_obj.get_service_directory(service_id)
    #     self.assertTrue(os.path.exists(service_dir))
    #     self.assertTrue(os.path.exists(
    #         os.path.join(service_dir, "bin/enstratus-dbgrant")))
    #
    #     self._backup_data(service_id, service_id + ".tar.gz", use_offsite=True, use_storage=True)

    @test_utils.system_changing
    @test_utils.s3_needed
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

        service_id = "asuccess_service"
        self._install_service(service_id,
                              self.backup_bucket,
                              self.simple_service)

        service_dir = self.conf_obj.get_service_directory(service_id)
        self.assertTrue(os.path.exists(service_dir))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-configure")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-stop")))
        self.assertTrue(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-start")))

        configuration_data = """
        This is some configuration data.
        That will be writen over there
        """

        arguments = {
            "configuration": configuration_data,
            "serviceId": service_id,
            "primaryCloudId": 1,
            "runAsUser": self.run_as_user,
            "primaryApiKey": os.environ["S3_ACCESS_KEY"],
            "primarySecretKey": os.environ["S3_SECRET_KEY"],
            "toBackupDirectory": "enstratiustests",
            "serviceImageFile": "success_service.tar.gz",
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
            arguments["primaryCloudId"],
            arguments["primaryApiKey"],
            arguments["primarySecretKey"],
            region_id="us_west_oregon")

        container = cloud.get_container(arguments["toBackupDirectory"])
        obj_list = cloud.list_container_objects(container)

        found = False
        for o in obj_list:
            ndx = o.name.find(dataSourceName)
            if ndx >= 0:
                found = True
                cloud.delete_object(o)

        self.assertTrue(found)


    @test_utils.system_changing
    @test_utils.s3_needed
    def test_grant_db_revoke_db(self):
        """
        install a service, start it, configure it in two ways, stop it, then
        delete the directory it was put into
        """
        service_id = "asuccess_service" + str(uuid.uuid4())
        self._install_service(service_id,
                              self.backup_bucket,
                              self.simple_service)

        service_dir = self.conf_obj.get_service_directory(service_id)
        self.assertTrue(os.path.exists(service_dir))
        self.assertTrue(os.path.exists(
            os.path.join(service_dir, "bin/enstratus-dbgrant")))


        cfg_data =\
        """
        This is some sample configuration data that will be passed to the
        dbgrant file.
        """ + str(uuid.uuid4())

        arguments = {
            "customerId": self.customer_id,
            "configuration": bytearray(cfg_data),
            "serviceId": service_id
        }
        doc = {
            "command": "grant_database_access",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertTrue(os.path.exists("/tmp/enstratus_dbgrant"))

        with open("/tmp/enstratus_dbgrant", "r") as fptr:
            secs = fptr.readline()
            parameters = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm >= start_time)

        with open("/tmp/enstratus_dbgrant.cfg", "r") as fptr:
            cfg_data_back = fptr.read()
        self.assertEqual(cfg_data_back, cfg_data)

        # test revoke
        arguments = {
            "configurationData": bytearray(cfg_data),
            "serviceId": service_id
        }
        doc = {
            "command": "revoke_database_access",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        with open("/tmp/enstratus_dbrevoke", "r") as fptr:
            secs = fptr.readline()
            parameters = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm >= start_time)

        with open("/tmp/enstratus_dbrevoke.cfg", "r") as fptr:
            cfg_data_back = fptr.read()
        self.assertEqual(cfg_data_back, cfg_data)

    def _backup_service(self, storage_delegate=False):

        service_id = "abackup_service" + str(uuid.uuid4())
        self._install_service(service_id,
                              self.backup_bucket,
                              self.simple_service)

        arguments = {
            "serviceId": service_id,
            "toBackupDirectory": self.backup_bucket,
            "primaryCloudId": 1,
            "primaryRegionId": self.default_s3_region,
            "primaryApiKey": os.environ["S3_ACCESS_KEY"],
            "primarySecretKey": os.environ["S3_SECRET_KEY"],
        }
        if storage_delegate:
            arguments["storageDelegate"] = 1
            arguments["storagePublicKey"] = os.environ["S3_ACCESS_KEY"]
            arguments["storagePrivateKey"] = os.environ["S3_SECRET_KEY"]

        doc = {
            "command": "backup_service",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        self.assertEquals(r["payload"]["return_code"], 0)
        self.assertEquals(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        self.assertEqual(jd["job_status"], "COMPLETE")


        with open("/tmp/service_backup", "r") as fptr:
            secs = fptr.readline()
            parameters = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        self.assertTrue(tm >= start_time)

        # verify that the file made it to the bucket
        backup_pattern = service_id + "-.*"
        prog = re.compile(backup_pattern)

        cloud = storagecloud.get_cloud_driver(
            arguments["primaryCloudId"],
            arguments["primaryApiKey"],
            arguments["primarySecretKey"],
            region_id=arguments["primaryRegionId"])

        container = cloud.get_container(arguments["toBackupDirectory"])
        obj_list = cloud.list_container_objects(container)

        found = False
        for o in obj_list:
            m = prog.match(o.name)
            if m:
                found = True
        self.assertTrue(found)

    @test_utils.system_changing
    @test_utils.s3_needed
    def test_backup_service(self):
        self._backup_service(storage_delegate=False)

    @test_utils.system_changing
    @test_utils.s3_needed
    def test_backup_service_storage(self):
        self._backup_service(storage_delegate=True)
