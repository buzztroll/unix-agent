from collections import namedtuple
import getpass
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

import dcm.agent.utils as utils
from dcm.agent.cmd import service, configure
from dcm.agent import config, dispatcher, storagecloud, parent_receive_q
from dcm.agent.messaging import reply, request
import dcm.agent.tests.utils as test_utils
import dcm.agent.tests.utils.test_connection as test_conn


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
    def _setup_storage_clouds(cls):
        env_str = "DCM_AGENT_STORAGE_CREDS"

        cls.storage_clouds = []
        if env_str not in os.environ:
            return

        path = os.environ[env_str]
        try:
            with open(path, "r") as fptr:
                cloud_lines = fptr.readlines()
        except Exception as ex:
            logging.error("Failed to setup storage clouds, continuing all "
                          "tests that do not require a storage cloud", ex)
            return

        for cloud_line in cloud_lines:
            cloud_endpoint = None
            cloud_account = None
            cloud_region = None
            c_a = cloud_line.split(" ")
            cloud_id = int(c_a.pop(0).strip())
            cloud_key = c_a.pop(0).strip()
            cloud_secret = c_a.pop(0).strip()
            if c_a:
                cloud_region = c_a.pop(0).strip()
            if c_a:
                cloud_endpoint = c_a.pop(0).strip()
            if c_a:
                cloud_account = c_a.pop(0).strip()

            CloudT = namedtuple('Cloud', 'id key secret endpoint account region')
            cloud = CloudT(cloud_id,
                           cloud_key,
                           cloud_secret,
                           cloud_endpoint,
                           cloud_account,
                           cloud_region)
            cls.storage_clouds.append(cloud)

    @classmethod
    def _setup_buckets(cls):
        cls.bucket = "dcmagenttests" + \
                            str(uuid.uuid4()).split("-")[0]
        cls.simple_service = "asimple_service.tar.gz"

        if not cls.storage_clouds:
            return

        etc_dir = os.path.dirname(os.path.dirname(__file__))
        tar_dir = tempfile.mkdtemp()
        tar_path = os.path.join(tar_dir, cls.simple_service)
        with tarfile.open(tar_path, "w:gz") as tar:
            for fname in os.listdir(
                    os.path.join(etc_dir, "etc", "simple_service")):
                tar.add(os.path.join(etc_dir, "etc",
                                     "simple_service", fname), arcname=fname)

        for cloud in cls.storage_clouds:
            cloud_driver = storagecloud.get_cloud_driver(
                cloud.id,
                cloud.key,
                cloud.secret,
                region_id=cloud.region,
                account=cloud.account,
                endpoint=cloud.endpoint)
            cloud_driver.create_container(cls.bucket)
            container = cloud_driver.get_container(cls.bucket)
            cloud_driver.upload_object(tar_path, container, cls.simple_service)

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
            cls._setup_storage_clouds()
            cls._setup_buckets()
        except Exception as ex:
            raise

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_base_path)

        for cloud in cls.storage_clouds:
            cloud_driver = storagecloud.get_cloud_driver(
                cloud.id,
                cloud.key,
                cloud.secret,
                region_id=cloud.region,
                account=cloud.account,
                endpoint=cloud.endpoint)
            try:
                container = cloud_driver.get_container(cls.bucket)
                obj_list = cloud_driver.list_container_objects(container)
                for o in obj_list:
                    cloud_driver.delete_object(o)
                cloud_driver.delete_container(container)
            except:
                pass

    def setUp(self):
        service._g_conn_for_shutdown = None

        self._event = threading.Event()

        test_conf_path = os.path.join(self.test_base_path, "etc", "agent.conf")
        self.conf_obj = config.AgentConfig([test_conf_path])
        utils.verify_config_file(self.conf_obj)
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
        handshake_doc["regionId"] = None
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
        nose.tools.eq_(r["payload"]["reply_type"], "string")
        nose.tools.eq_(r["payload"]["return_code"], 0)

        # TODO verify that this matches the output of the command

    def test_get_agent_data(self):
        doc = {
            "command": "get_agent_data",
            "arguments": {}
        }
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        nose.tools.eq_(r["payload"]["reply_type"], "agent_data")
        nose.tools.eq_(r["payload"]["return_code"], 0)

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
        nose.tools.eq_(r["payload"]["return_code"], 0)

        pw_ent = pwd.getpwnam(user_name)

        nose.tools.eq_(pw_ent.pw_name, user_name)

        doc = {
            "command": "remove_user",
            "arguments": {"userId": user_name}}

        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        try:
            pwd.getpwnam(user_name)
            nose.tools.ok_(False, "should have raised an exception")
        except KeyError:
            pass

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
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(socket.gethostname(), new_hostname)

        customer_user = utils.make_id_string("c", cust)
        pw_ent = pwd.getpwnam(customer_user)
        nose.tools.eq_(pw_ent.pw_name, customer_user)

    def test_list_devices(self):
        doc = {
            "command": "list_devices",
            "arguments": {}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

        # TODO verify that this matches the output of the command

    def test_get_service_states(self):
        doc = {
            "command": "get_service_states",
            "arguments": {"agent_token": None}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

        # TODO verify that this matches the output of the command

    @test_utils.system_changing
    def test_rename(self):
        orig_hostname = socket.gethostname()

        new_hostname = "buzztroll"
        doc = {
            "command": "rename",
            "arguments": {"serverName": new_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

        nose.tools.eq_(socket.gethostname(), new_hostname)

        doc = {
            "command": "rename",
            "arguments": {"serverName": orig_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

        nose.tools.eq_(socket.gethostname(), orig_hostname)

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
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]

        return jd

    def _install_service(self, service_id, bucket, fname, cloud_tuple,
                         other_storage=False):

        # test install
        arguments = {
            "customerId": self.customer_id,
            "serviceId": service_id,
            "cloudId": cloud_tuple.id,
            "runAsUser": self.run_as_user,
            "apiAccessKey": cloud_tuple.key,
            "apiSecretKey": cloud_tuple.secret,
            "serviceImageDirectory": bucket,
            "providerRegionId": cloud_tuple.region,
            "apiEndpoint": cloud_tuple.endpoint,
            "apiAccount": cloud_tuple.account,
            "serviceImageFile": fname
        }
        if other_storage:
            arguments["storageAccessKey"] = cloud_tuple.key
            arguments["storageSecretKey"] = cloud_tuple.secret
            arguments["storageDelegate"] = cloud_tuple.id
            arguments["storageEndpoint"] = cloud_tuple.endpoint
            arguments["storageAccount"] = cloud_tuple.account

        doc = {
            "command": "install_service",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        service_dir = self.conf_obj.get_service_directory(service_id)
        nose.tools.ok_(os.path.exists(service_dir))
        nose.tools.ok_(os.path.exists(
            os.path.join(service_dir, "bin/enstratus-configure")))
        nose.tools.ok_(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-stop")))
        nose.tools.ok_(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-start")))

    def test_service_install_only(self):
        for b in (True, False):
            for i in range(-1, len(self.storage_clouds) - 1):
                primary = self.storage_clouds[i]
                secondary = self.storage_clouds[i + 1]
                if primary == secondary:
                    secondary = None
                yield self._service_install_only, primary, secondary, b

    def _service_install_only(self, primary, secondary, other_store):
        service_id = "aservice" + str(uuid.uuid4()).split("-")[0]
        self._install_service(service_id,
                              self.bucket,
                              self.simple_service,
                              primary,
                              other_storage=True)

    def test_alt_service_install_data_source(self):
        for b in (True, False):
            for i in range(-1, len(self.storage_clouds) - 1):
                primary = self.storage_clouds[i]
                secondary = self.storage_clouds[i + 1]
                if primary == secondary:
                    secondary = None
                yield self.alt_service_install, primary, secondary, b

    def alt_service_install(self, primary, secondary, os):
        service_id = "aservice" + str(uuid.uuid4()).split("-")[0]
        self._install_service(service_id,
                              self.bucket,
                              self.simple_service,
                              primary,
                              other_storage=os)

        configuration_data = """test config data"""
        arguments = {
            "customerId": self.customer_id,
            "serviceId": service_id,
            "cloudId": primary.id,
            "runAsUser": self.run_as_user,
            "apiAccessKey": primary.key,
            "apiSecretKey": primary.secret,
            "configuration": configuration_data,
            "imageDirectory": self.bucket,
            # pretend the same tarball is the data set
            "dataSourceImage": self.simple_service,
            "storagePublicKey": primary.key,
            "storagePrivateKey": primary.secret,
            "storageDelegate": primary.id,
            "regionId": primary.region
        }
        doc = {
            "command": "install_data_source",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "job_description")
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

    def test_install_start_stop_configure_service(self):
        """
        install a service, start it, configure it in two ways, stop it, then
        delete the directory it was put into
        """
        for b in (True, False):
            for i in range(-1, len(self.storage_clouds) - 1):
                primary = self.storage_clouds[i]
                secondary = self.storage_clouds[i + 1]
                if primary == secondary:
                    secondary = None
                yield self._install_start_stop_configure_service, primary, secondary, b

    def _install_start_stop_configure_service(self, primary, secondary, b):
        service_id = "aservice" + str(uuid.uuid4()).split("-")[0]
        self._install_service(service_id,
                              self.bucket,
                              self.simple_service,
                              primary,
                              other_storage=b)

        service_dir = self.conf_obj.get_service_directory(service_id)
        nose.tools.ok_(os.path.exists(service_dir))
        nose.tools.ok_(os.path.exists(
            os.path.join(service_dir, "bin/enstratus-configure")))
        nose.tools.ok_(os.path.exists(os.path.join(service_dir,
                                                    "bin/enstratus-stop")))
        nose.tools.ok_(os.path.exists(os.path.join(service_dir,
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
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.ok_(os.path.exists("/tmp/service_start"))

        with open("/tmp/service_start", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        nose.tools.ok_(tm >= start_time)

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
        nose.tools.eq_(r["payload"]["return_code"], 0)
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        nose.tools.ok_(os.path.exists("/tmp/service_configure"))

        with open("/tmp/service_configure", "r") as fptr:
            secs = fptr.readline()
            params = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        nose.tools.ok_(tm >= start_time)
        p_a = params.split()
        nose.tools.ok_(len(p_a), 2)

        cfg_file = os.path.join(service_dir, "cfg", "enstratiusinitd.cfg")
        nose.tools.ok_(os.path.exists(cfg_file))

        with open(cfg_file, "r") as fptr:
            data = fptr.read()
            nose.tools.ok_(data, configuration_data)

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
            "sslChain": "thisisthesslschain"
        }
        doc = {
            "command": "configure_service_with_ssl",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        nose.tools.ok_(os.path.exists("/tmp/service_configure"))

        with open("/tmp/service_configure", "r") as fptr:
            secs = fptr.readline()
            params = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        nose.tools.ok_(tm >= start_time)
        p_a = params.split()
        nose.tools.eq_(len(p_a), 6)

        cfg_file = os.path.join(service_dir, "cfg", "enstratiusinitd.cfg")
        nose.tools.ok_(os.path.exists(cfg_file))

        with open(cfg_file, "r") as fptr:
            data = fptr.read()
            nose.tools.eq_(data, configuration_data)

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
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "string_array")
        service_array = r["payload"]["reply_object"]

        nose.tools.ok_(service_id in service_array)
        nose.tools.eq_(service_array[service_array.index(service_id) + 1],
                         'OK')

        # install data source
        arguments = {
            "customerId": self.customer_id,
            "serviceId": service_id,
            "cloudId": primary.id,
            "runAsUser": self.run_as_user,
            "apiAccessKey": primary.key,
            "apiSecretKey": primary.secret,
            "configuration": configuration_data,
            "imageDirectory": self.bucket,
            "dataSourceImage": self.simple_service,
            "regionId": primary.region
        }
        doc = {
            "command": "install_data_source",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "job_description")
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

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
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.ok_(os.path.exists("/tmp/service_stop"))

        with open("/tmp/service_stop", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        nose.tools.ok_(tm >= start_time)
        shutil.rmtree(service_dir)

    @test_utils.system_changing
    def test_start_services(self):
        """
        install a service, start it, configure it in two ways, stop it, then
        delete the directory it was put into
        """
        # just install from the first storage cloud in the list
        if not self.storage_clouds:
            raise skip.SkipTest("No storage clouds configured")

        primary_cloud = self.storage_clouds[1]
        service_id1 = "aone_service" + str(uuid.uuid4()).split("-")[0]
        self._install_service(service_id1,
                              self.bucket,
                              self.simple_service,
                              primary_cloud)

        service_id2 = "atwo_service" + str(uuid.uuid4()).split("-")[0]
        self._install_service(service_id2,
                              self.bucket,
                              self.simple_service,
                              primary_cloud)

        # test start
        arguments = {
            "serviceIds": [service_id1, service_id2]
        }
        doc = {
            "command": "start_services",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.ok_(os.path.exists("/tmp/service_start"))

        with open("/tmp/service_start", "r") as fptr:
            secs = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        nose.tools.ok_(tm >= start_time)

        # get service state
        arguments = {
        }
        doc = {
            "command": "get_service_states",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "string_array")
        service_array = r["payload"]["reply_object"]

        nose.tools.ok_(service_id1 in service_array)
        nose.tools.ok_(service_id2 in service_array)
        nose.tools.eq_(service_array[service_array.index(service_id1) + 1],
                         'OK')
        nose.tools.eq_(service_array[service_array.index(service_id2) + 1],
                         'OK')

    def _backup_data(self,
                     s_id,
                     file_path,
                     primary,
                     secondary,
                     use_storage=False):

        object_name = "objname" + str(uuid.uuid4()).split("-")[0]
        cfg = """
        A bunch of config data
        """ + str(uuid.uuid4())

        cloud_list = [primary]
        arguments = {
            "configuration": cfg,
            "serviceId": s_id,
            "primaryCloudId": primary.id,
            "runAsUser": self.run_as_user,
            "primaryApiKey": primary.key,
            "primarySecretKey": primary.secret,
            "toBackupDirectory": self.bucket,
            "serviceImageFile": file_path,
            "dataSourceName": object_name,
            "primaryRegionId": primary.region
        }
        if use_storage:
            arguments["storageDelegate"] = primary.id
            arguments["storageApiKey"] = primary.key
            arguments["storageSecretKey"] = primary.secret

        if secondary:
            cloud_list.append(secondary)
            arguments["secondaryCloudId"] = secondary.id
            arguments["secondaryApiKey"] = secondary.key
            arguments["secondarySecretKey"] = secondary.secret
            arguments["secondaryRegionId"] = secondary.region
            if use_storage:
                arguments["secondaryStorageDelegate"] = secondary.id
                arguments["secondaryStorageApiKey"] = secondary.key
                arguments["secondaryStorageSecretKey"] = secondary.secret

        doc = {
            "command": "backup_data_source",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        for cloud in cloud_list:
            cloud_driver = storagecloud.get_cloud_driver(
                cloud.id,
                cloud.key,
                cloud.secret,
                region_id=cloud.region)

            found = False
            container = cloud_driver.get_container(self.bucket)
            obj_list = cloud_driver.list_container_objects(container)
            for obj in obj_list:
                ndx = obj.name.find(object_name)
                if ndx >= 0:
                    found = True
            nose.tools.ok_(found)

    def test_backup_data_source(self):
        if not self.storage_clouds:
            raise skip.SkipTest("No storage clouds are configured")

        for b in (True, False):
            for i in range(-1, len(self.storage_clouds) - 1):
                primary = self.storage_clouds[i]
                secondary = self.storage_clouds[i + 1]
                if primary == secondary:
                    secondary = None
                yield self._backup_data_source, primary, secondary, b

        if len(self.storage_clouds) > 1:
            yield self._backup_data_source, self.storage_clouds[0], None, True
            yield self._backup_data_source, self.storage_clouds[0], None, False

    def _backup_data_source(self, primary, secondary, use_storage):
        service_id = "aservice_for_backup" + str(uuid.uuid4())
        self._install_service(service_id,
                              self.bucket,
                              self.simple_service,
                              primary)

        service_dir = self.conf_obj.get_service_directory(service_id)
        nose.tools.ok_(os.path.exists(service_dir))
        nose.tools.ok_(os.path.exists(
            os.path.join(service_dir, "bin/enstratus-dbgrant")))
        self._backup_data(service_id, service_id + ".tar.gz", primary,
                          secondary, use_storage=use_storage)

    @test_utils.system_changing
    def test_grant_db_revoke_db(self):
        """
        install a service, start it, configure it in two ways, stop it, then
        delete the directory it was put into
        """
        if not self.storage_clouds:
            raise skip.SkipTest("No storage clouds are configured")
        # just use the first cloud.  install_service is well tested on
        # all clouds elsewhere

        store_cloud = self.storage_clouds[0]

        service_id = "asuccess_service" + str(uuid.uuid4())
        self._install_service(service_id,
                              self.bucket,
                              self.simple_service,
                              store_cloud)

        service_dir = self.conf_obj.get_service_directory(service_id)
        nose.tools.ok_(os.path.exists(service_dir))
        nose.tools.ok_(os.path.exists(
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
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.ok_(os.path.exists("/tmp/enstratus_dbgrant"))

        with open("/tmp/enstratus_dbgrant", "r") as fptr:
            secs = fptr.readline()
            parameters = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        nose.tools.ok_(tm >= start_time)

        with open("/tmp/enstratus_dbgrant.cfg", "r") as fptr:
            cfg_data_back = fptr.read()
        nose.tools.eq_(cfg_data_back, cfg_data)

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
        nose.tools.ok_(tm >= start_time)

        with open("/tmp/enstratus_dbrevoke.cfg", "r") as fptr:
            cfg_data_back = fptr.read()
        nose.tools.eq_(cfg_data_back, cfg_data)

    def _backup_service(self, primary, secondary, storage_delegate):

        service_id = "abackup_service" + str(uuid.uuid4())
        self._install_service(service_id,
                              self.bucket,
                              self.simple_service,
                              primary)

        arguments = {
            "serviceId": service_id,
            "toBackupDirectory": self.bucket,
            "primaryCloudId": primary.id,
            "primaryRegionId": primary.region,
            "primaryApiKey": primary.key,
            "primarySecretKey": primary.secret,
        }
        if storage_delegate:
            arguments["storageDelegate"] = primary.id
            arguments["storagePublicKey"] = primary.key
            arguments["storagePrivateKey"] = primary.secret

        if secondary:
            arguments["secondaryCloudId"] = secondary.id
            arguments["secondaryRegionId"] = secondary.region
            arguments["secondaryApiKey"] = secondary.key
            arguments["secondarySecretKey"] = secondary.secret
            arguments["secondaryApiEndpoint"] = secondary.endpoint
            arguments["secondaryApiAccount"] = secondary.account
            if storage_delegate:
                arguments["secondaryStorageDelegate"] = secondary.id
                arguments["secondaryStoragePublicKey"] = secondary.key
                arguments["secondaryStoragePrivateKey"] = secondary.secret
                arguments["secondaryStorageEndpoint"] = secondary.endpoint
                arguments["secondaryStorageAccount"] = secondary.account

        doc = {
            "command": "backup_service",
            "arguments": arguments
        }
        start_time = datetime.datetime.now().replace(microsecond=0)
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        with open("/tmp/service_backup", "r") as fptr:
            secs = fptr.readline()
            parameters = fptr.readline()
        tm = datetime.datetime.utcfromtimestamp(float(secs))
        nose.tools.ok_(tm >= start_time)

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
        nose.tools.ok_(found)

    def test_backup_service(self):
        for b in (True, False):
            for i in range(-1, len(self.storage_clouds) - 1):
                primary = self.storage_clouds[i]
                secondary = self.storage_clouds[i + 1]
                if primary == secondary:
                    secondary = None
                yield self._backup_service, primary, secondary, b

        if len(self.storage_clouds) > 1:
            yield self._backup_service, self.storage_clouds[0], None, True
            yield self._backup_service, self.storage_clouds[0], None, False

    def _upload_enstratius_config_scripts(self, primary, files_uuids):
        # load up a bunch of scripts that will be downloaded and run.
        # the scripts just echo a uuid to a file and after config
        # the test will check each file for the right uuid
        cloud = storagecloud.get_cloud_driver(
            primary.id,
            primary.key,
            primary.secret,
            region_id=primary.region)

        scripts = []
        for f, u in files_uuids:
            osf, tmp_path = tempfile.mkstemp()
            os.write(osf, "#!/usr/bin/env bash")
            os.write(osf, os.linesep)
            os.write(osf, "echo %s > /tmp/%s" % (u, f))
            os.write(osf, os.linesep)
            os.write(osf, "exit 0")
            os.write(osf, os.linesep)
            os.close(osf)

            container = cloud.get_container(self.bucket)
            cloud.upload_object(tmp_path, container, f)
            scripts.append(os.path.join(self.bucket, f))
        return scripts

    @test_utils.system_changing
    def test_configure_server_with_enstratius(self):
        if not self.storage_clouds:
            raise skip.SkipTest("No storage clouds are configured")
        # just use the first cloud.  install_service is well tested on
        # all clouds elsewhere
        primary = self.storage_clouds[0]

        files_uuids = [
            ("script_run"+str(uuid.uuid4()), str(uuid.uuid4())),
            ("script_run"+str(uuid.uuid4()), str(uuid.uuid4())),
            ("script_run"+str(uuid.uuid4()), str(uuid.uuid4()))]

        script_files = self._upload_enstratius_config_scripts(
            primary, files_uuids)
        arguments = {
            "configType": "ENSTRATUS",
            "providerRegionId": primary.region,
            "storageDelegate": primary.id,
            "scriptFiles": script_files,
            "storagePublicKey": primary.key,
            "storagePrivateKey": primary.secret,
            "personalityFiles": [],
        }
        doc = {
            "command": "configure_server_16",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        for f, u in files_uuids:
            f_path = os.path.join("/tmp", f)
            print f_path
            nose.tools.ok_(os.path.exists(f_path))
            with open(f_path, "r") as fptr:
                line = fptr.readline().strip()
                nose.tools.eq_(line, u)

    @test_utils.system_changing
    def test_configure_server_17_with_enstratius(self):
        if not self.storage_clouds:
            raise skip.SkipTest("No storage clouds are configured")
        # just use the first cloud.  install_service is well tested on
        # all clouds elsewhere
        primary = self.storage_clouds[0]

        files_uuids = [
            ("script_run"+str(uuid.uuid4()), str(uuid.uuid4())),
            ("script_run"+str(uuid.uuid4()), str(uuid.uuid4())),
            ("script_run"+str(uuid.uuid4()), str(uuid.uuid4()))]

        script_files = self._upload_enstratius_config_scripts(
            primary, files_uuids)
        arguments = {
            "configType": "ENSTRATUS",
            "providerRegionId": primary.region,
            "storageDelegate": primary.id,
            "scriptFiles": script_files,
            "storagePublicKey": primary.key,
            "storagePrivateKey": primary.secret,
            "personalityFiles": [],
        }
        doc = {
            "command": "configure_server_17",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)
        nose.tools.eq_(r["payload"]["reply_type"], "job_description")

        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        for f, u in files_uuids:
            f_path = os.path.join("/tmp", f)
            print f_path
            nose.tools.ok_(os.path.exists(f_path))
            with open(f_path, "r") as fptr:
                line = fptr.readline().strip()
                nose.tools.eq_(line, u)

    def test_unmount_something_not_mounted(self):
        arguments = {
            "deviceId": "/dev/notreal",
        }
        doc = {
            "command": "unmount_volume",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

    @test_utils.system_changing
    def test_rename_bad_name(self):
        new_hostname = "@#@#$"
        doc = {
            "command": "rename",
            "arguments": {"serverName": new_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.ok_(r["payload"]["return_code"] != 0)

    @test_utils.system_changing
    def test_initialize_rename_error(self):
        cust = 10l
        orig_hostname = socket.gethostname()
        new_hostname = "#@#*&%$"
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
        nose.tools.ok_(r["payload"]["return_code"] != 0)
        nose.tools.eq_(socket.gethostname(), orig_hostname)


    @test_utils.system_changing
    def test_mount_variety(self):
        mount_point = tempfile.mkdtemp()
        device_id = "sdb"

        mappings = utils.get_device_mappings(self.conf_obj)
        for dm in mappings:
            if dm['device_id'] == device_id:
                if dm['mount_point'] != mount_point:
                    raise Exception("The device is already mounted")

        doc = {
            "command": "mount_volume",
            "arguments": {"formatVolume": True,
                          "fileSystem": "ext3",
                          "raidLevel": "NONE",
                          "encryptionKey": None,
                          "mountPoint": mount_point,
                          "devices": [device_id]}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        found = False
        mappings = utils.get_device_mappings(self.conf_obj)
        for dm in mappings:
            if dm['device_id'] == device_id:
                found = True
                nose.tools.eq_(dm['mount_point'], mount_point)
        nose.tools.ok_(found)

        doc = {
            "command": "mount_volume",
            "arguments": {"formatVolume": False,
                          "fileSystem": "ext3",
                          "raidLevel": "NONE",
                          "encryptionKey": None,
                          "mountPoint": mount_point,
                          "devices": ["sdb"]}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        arguments = {
            "deviceId": device_id,
        }
        doc = {
            "command": "unmount_volume",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

    @test_utils.system_changing
    def test_mount_encryption(self):
        enc_str = "ENCRYPTED_FILE_ENV"

        if enc_str not in os.environ:
            raise skip.SkipTest("set %s to try encryption tests" % enc_str)

        enc_key = os.environ["ENCRYPTED_FILE_ENV"]
        mount_point = tempfile.mkdtemp()
        device_id = "sdb"

        mappings = utils.get_device_mappings(self.conf_obj)
        for dm in mappings:
            if dm['device_id'] == device_id:
                if dm['mount_point'] != mount_point:
                    raise Exception("The device is already mounted")

        doc = {
            "command": "mount_volume",
            "arguments": {"formatVolume": True,
                          "fileSystem": "ext3",
                          "raidLevel": "NONE",
                          "encryptionKey": enc_key,
                          "mountPoint": mount_point,
                          "devices": [device_id]}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        arguments = {
            "deviceId": device_id,
        }
        doc = {
            "command": "unmount_volume",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

