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
import dcm.agent.tests.utils.general as test_utils
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
    def _setup_storage_clouds(cls):
        env_str = "DCM_AGENT_STORAGE_CREDS"

        cls.storage_clouds = []
        if env_str not in os.environ:
            return

        path = os.environ[env_str]
        if not os.path.exists(path):
            return
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

            cloud = CloudT(cloud_id,
                           cloud_key,
                           cloud_secret,
                           cloud_endpoint,
                           cloud_account,
                           cloud_region)
            cls.storage_clouds.append(cloud)

    @classmethod
    def _setup_buckets(cls):
        cls.bucket = "dcmagenttests" + str(uuid.uuid4()).split("-")[0]
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
        try:
            cls._setup_storage_clouds()
            cls._setup_buckets()
        except Exception as ex:
            raise

    @classmethod
    def tearDownClass(cls):
        logger.clear_dcm_logging()

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
        self.db = persistence.SQLiteAgentDB(
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
                          "firstName": "buzz",
                          "lastName": "troll",
                          "authentication": "public key data",
                          "administrator": False}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        print r["payload"]["return_code"]
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

    def _build_underscore_dash_names(self, user_name):

        doc = {
            "command": "add_user",
            "arguments": {"customerId": self.customer_id,
                          "userId": user_name,
                          "firstName": "buzz",
                          "lastName": "troll",
                          "authentication": "public key data",
                          "administrator": False}}

        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        msg = 'this following name failed:  ' + user_name

        try:
            nose.tools.ok_(r["payload"]["return_code"] != 0, msg)

        finally:
            try:  # delete and clean up user
                pw_ent = pwd.getpwnam(user_name)
                if pw_ent is not None:
                    os.system('userdel -r %s' % user_name)
            except Exception, e:  # show exception
                print e

    def test_add_underscore_dash_username_fails(self):
        """
        :return: tests to show that names created
                 with -,_ at beginning or end of username fail
        """
        if "SYSTEM_CHANGING_TEST" not in os.environ:
            raise skip.SkipTest('skipping')

        usernames = ['-bob', '_bob', 'bob_', 'bob-',
                     '-bob-', '_bob_', '_bob-', '-bob_']

        for user_name in usernames:
            yield self._build_underscore_dash_names, user_name

    def _build_fake_names(self, sc):
        user_name = 'Bob' + sc

        doc = {
            "command": "add_user",
            "arguments": {"customerId": self.customer_id,
                          "userId": user_name,
                          "firstName": "buzz",
                          "lastName": "troll",
                          "authentication": "public key data",
                          "administrator": False}}

        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        msg = 'special char is ' + sc

        try:
            nose.tools.ok_(r["payload"]["return_code"] != 0, msg)
        finally:
            try:  # delete and clean up user
                pw_ent = pwd.getpwnam(user_name)
                if pw_ent is not None:
                    os.system('userdel -r %s' % user_name)
            except Exception as e:  # show exception
                print e

    def test_add_special_char_username_fails(self):
        """
        :return: tests to show that names created
                 with things in spec_chars fail
        """
        if "SYSTEM_CHANGING_TEST" not in os.environ:
            raise skip.SkipTest('skipping')

        spec_chars = ['*', '&', '!', '?', '/', '\\', '.', '^', '$', '(', ')', '{', '}', '[', ']']

        for sc in spec_chars:
            yield self._build_fake_names, sc

    @test_utils.system_changing
    def test_add_admin_user_remove_user(self):
        user_name = "dcm" + str(random.randint(10, 99))

        doc = {
            "command": "add_user",
            "arguments": {"customerId": self.customer_id,
                          "userId": user_name,
                          "firstName": "buzz",
                          "lastName": "troll",
                          "authentication": "public key data",
                          "administrator": True}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

        pw_ent = pwd.getpwnam(user_name)

        # TODO figure out a safe way to verify that sudo was added

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

    @test_utils.skip_docker
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

    @test_utils.skip_docker
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

    @test_utils.skip_docker
    @test_utils.system_changing
    def test_rename_bad_hostname(self):
        orig_hostname = socket.gethostname()

        new_hostname = "@pp1#"
        doc = {
            "command": "rename",
            "arguments": {"serverName": new_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.ok_(r["payload"]["return_code"] == 0)
        nose.tools.eq_(socket.gethostname(), "pp1")

        doc = {
            "command": "rename",
            "arguments": {"serverName": orig_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

        nose.tools.eq_(socket.gethostname(), orig_hostname)

    @test_utils.skip_docker
    @test_utils.system_changing
    def test_rename_long_hostname(self):
        orig_hostname = socket.gethostname()

        new_hostname = ''.join(random.choice(
            string.ascii_letters) for n in range(256))

        doc = {
            "command": "rename",
            "arguments": {"serverName": new_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        print socket.gethostname()
        nose.tools.ok_(r["payload"]["return_code"] != 0)
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

        time.sleep(0.1)

        return jd

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
            "configuration": base64.b64encode(bytearray(cfg)),
            "serviceId": s_id,
            "primaryCloudId": primary.id,
            "runAsUser": self.run_as_user,
            "primaryApiKey": base64.b64encode(bytearray(primary.key)),
            "primarySecretKey": base64.b64encode(bytearray(primary.secret)),
            "toBackupDirectory": self.bucket,
            "serviceImageFile": file_path,
            "dataSourceName": object_name,
            "primaryRegionId": primary.region
        }
        if use_storage:
            arguments["storageDelegate"] = primary.id
            arguments["storageApiKey"] = \
                base64.b64encode(bytearray(primary.key))
            arguments["storageSecretKey"] = \
                base64.b64encode(bytearray(primary.secret))

        if secondary:
            cloud_list.append(secondary)
            arguments["secondaryCloudId"] = secondary.id
            arguments["secondaryApiKey"] = \
                base64.b64encode(bytearray(secondary.key))
            arguments["secondarySecretKey"] = \
                base64.b64encode(bytearray(secondary.secret))
            arguments["secondaryRegionId"] = secondary.region
            if use_storage:
                arguments["secondaryStorageDelegate"] = secondary.id
                arguments["secondaryStorageApiKey"] = \
                    base64.b64encode(bytearray(secondary.key))
                arguments["secondaryStorageSecretKey"] = \
                    base64.b64encode(bytearray(secondary.secret))

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
    def test_configure_server_unknown_type_error(self):
        if not self.storage_clouds:
            raise skip.SkipTest("No storage clouds are configured")
        primary = self.storage_clouds[0]

        files_uuids = []

        script_files = self._upload_enstratius_config_scripts(
            primary, files_uuids)
        arguments = {
            "configType": "NOReal",
            "providerRegionId": primary.region,
            "storageDelegate": primary.id,
            "scriptFiles": script_files,
            "storagePublicKey": base64.b64encode(bytearray(primary.key)),
            "storagePrivateKey": base64.b64encode(bytearray(primary.secret)),
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
        nose.tools.eq_(jd["job_status"], "ERROR")
        nose.tools.ok_(jd["message"])

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

    @test_utils.skip_docker
    @test_utils.system_changing
    def test_rename_bad_name(self):
        orig_hostname = socket.gethostname()

        new_hostname = "@#@#$"
        doc = {
            "command": "rename",
            "arguments": {"serverName": new_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.ok_(r["payload"]["return_code"] == 0)
        nose.tools.eq_(socket.gethostname(), "unknown")

        doc = {
            "command": "rename",
            "arguments": {"serverName": orig_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

        nose.tools.eq_(socket.gethostname(), orig_hostname)


    @test_utils.skip_docker
    @test_utils.system_changing
    def test_initialize_rename_error(self):
        cust = 10l
        orig_hostname = socket.gethostname()
        new_hostname = "....."
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
        mount_point = os.path.join(tempfile.mkdtemp(), "mnt")

        if os.path.exists("/dev/sdb"):
            device_id = "sdb"
        elif os.path.exists("/dev/hdb"):
            device_id = "hdb"
        else:
            raise skip.SkipTest("No second drive was found")

        mappings = utils.get_device_mappings(self.conf_obj)
        for dm in mappings:
            if dm['device_id'] == device_id:
                os.system("umount " + dm['mount_point'])


        print device_id
        mappings = utils.get_device_mappings(self.conf_obj)
        for dm in mappings:
            if dm['device_id'] == device_id:
                if dm['mount_point'] != mount_point:
                    raise skip.SkipTest("The device is already mounted")

        doc = {
            "command": "mount_volume",
            "arguments": {"formatVolume": True,
                          "fileSystem": "ext3",
                          "raidLevel": "NONE",
                          "encryptedFsEncryptionKey": None,
                          "mountPoint": mount_point,
                          "devices": [device_id]}}
        print "trying to mount"
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")
        print "done mount"

        found = False
        mappings = utils.get_device_mappings(self.conf_obj)
        for dm in mappings:
            if dm['device_id'] == device_id:
                found = True
                nose.tools.eq_(dm['mount_point'], mount_point)
        nose.tools.ok_(found)

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

        mount_point = os.path.join(tempfile.mkdtemp(), "mnt2")
        doc = {
            "command": "mount_volume",
            "arguments": {"formatVolume": True,
                          "fileSystem": "ext3",
                          "raidLevel": "NONE",
                          "encryptedFsEncryptionKey": None,
                          "mountPoint": mount_point,
                          "devices": [device_id]}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")
        print "done format"

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
        mount_point = os.path.join(tempfile.mkdtemp(), "mnt")
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
                          "encryptedFsEncryptionKey":
                              base64.b64encode(bytearray(enc_key)),
                          "mountPoint": mount_point,
                          "devices": [device_id]}}
        req_rpc = self._rpc_wait_reply(doc)
        r = req_rpc.get_reply()
        jd = r["payload"]["reply_object"]
        while jd["job_status"] in ["WAITING", "RUNNING"]:
            jd = self._get_job_description(jd["job_id"])
        nose.tools.eq_(jd["job_status"], "COMPLETE")

        arguments = {
            "deviceId": "es" + device_id,
            "encrypted": True
        }
        doc = {
            "command": "unmount_volume",
            "arguments": arguments
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

    def test_upgrade(self):
        try:
            print "starting upgrade"
            _, tmpfname = tempfile.mkstemp()
            _, exefname = tempfile.mkstemp()
            exe_data = """#!/bin/bash
                          echo $@ > %s
                       """ % tmpfname

            url = "file:///%s" % exefname
            newVersion = "10.100.newversion"
            with open(exefname, "w") as fptr:
                fptr.write(exe_data)

            doc = {
                "command": "upgrade",
                "arguments": {"url": url,
                              "newVersion": newVersion,
                              "args": ["arg1", "arg2"]}
            }
            print "sending upgrade"
            req_reply = self._rpc_wait_reply(doc)
            r = req_reply.get_reply()
            nose.tools.eq_(r["payload"]["return_code"], 0)

            print "verify upgrade"
            with open(tmpfname, "r") as fptr:
                line = fptr.readline()
            nose.tools.ok_(line)
            la = line.split()

            nose.tools.eq_(la[0], newVersion)
            nose.tools.eq_(la[1], dcm.agent.g_version)
        except Exception as ex:
            with open("/tmp/SUP", "w") as fptr:
                fptr.write("got here")
                fptr.write(os.linesep)
                try:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_tb(exc_traceback, file=fptr)
                except Exception as ex2:
                    fptr.write(str(ex2.message))
                    fptr.write(os.linesep)
                fptr.write(str(ex))
                fptr.write(os.linesep)
                fptr.write(ex.message)
                fptr.write(os.linesep)
                fptr.write(test_utils.build_assertion_exception("tester"))
            print ex
            print test_utils.build_assertion_exception("tester")
            nose.tools.ok_(False, ex.message)

    def test_run_script(self):
        _, tmpfname = tempfile.mkstemp()
        _, exefname = tempfile.mkstemp()
        args = ["arg1", "hello", "args3"]
        exe_data = """#!/bin/bash
                      echo $@ > %s
                   """ % tmpfname

        sha256 = hashlib.sha256()
        sha256.update(exe_data)
        checksum = sha256.hexdigest()

        doc = {
            "command": "run_script",
            "arguments": {
                "b64script": base64.b64encode(exe_data),
                "arguments": args,
                "checksum": checksum
            }
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.eq_(r["payload"]["return_code"], 0)

        with open(tmpfname, "r") as fptr:
            line = fptr.readline()
        nose.tools.ok_(line)
        la = line.split()

        nose.tools.eq_(la, args)

    @test_utils.system_changing
    def test_configure_server_with_chef(self):
        _, tmpfname = tempfile.mkstemp()
        fake_chef_script = """#!/bin/bash
        echo $@ > %s
        """ % tmpfname

        chef_script_path = os.path.join(
            self.test_base_path, "bin", "runConfigurationManagement-CHEF")

        with open(chef_script_path, "w") as fptr:
            fptr.write(fake_chef_script)
        os.chmod(chef_script_path, 0x755)

        runListIds = ["recipe[git]", "recipe[2]"]
        confClientName = "confname"

        arguments = {
            "configType": "CHEF",
            "runListIds": runListIds,
            "configClientName": confClientName
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

        with open(tmpfname, "r") as fptr:
            lines = fptr.readlines()
        nose.tools.ok_(len(lines) >= 1)

        line1_a = lines[0].split()
        nose.tools.eq_(line1_a[1], confClientName)

    @test_utils.system_changing
    def test_configure_server_with_puppet(self):
        _, tmpfname = tempfile.mkstemp()
        fake_chef_script = """#!/bin/bash
        echo $@ > %s
        """ % tmpfname

        chef_script_path = os.path.join(
            self.test_base_path, "bin", "runConfigurationManagement-PUPPET")

        with open(chef_script_path, "w") as fptr:
            fptr.write(fake_chef_script)
        os.chmod(chef_script_path, 0x755)

        confClientName = "confname"
        configCert = base64.b64encode(bytearray(str(uuid.uuid4())))
        configKey = base64.b64encode(bytearray(str(uuid.uuid4())))

        arguments = {
            "configType": "PUPPET",
            "configClientName": confClientName,
            "configCert": configCert,
            "configKey": configKey
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

        with open(tmpfname, "r") as fptr:
            lines = fptr.readlines()
        nose.tools.ok_(len(lines) >= 1)

        line1_a = lines[0].split()
        nose.tools.eq_(line1_a[1], confClientName)

    def test_bad_arguments(self):
        orig_hostname = socket.gethostname()

        new_hostname = "@pp1#"
        doc = {
            "command": "rename",
            "arguments": {"NotAName": new_hostname}
        }
        req_reply = self._rpc_wait_reply(doc)
        r = req_reply.get_reply()
        nose.tools.ok_(r["payload"]["return_code"] != 0)
        nose.tools.eq_(socket.gethostname(), orig_hostname)
