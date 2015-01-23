import base64
import hashlib
import os
import tempfile
import unittest
import boto
import uuid
import logging
import sys

from dcm.agent import config
import dcm.agent.jobs.builtin.fetch_run as fetch_plugin
import dcm.agent.jobs.builtin.run_script as run_script_plugin
import dcm.agent.tests.utils.general as test_utils
from dcm.agent import exceptions


class TestFetchExePlugin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        if test_utils.S3_ACCESS_KEY_ENV not in os.environ or test_utils.S3_SECRET_KEY_ENV not in os.environ:
            return

        basedir = os.path.dirname((os.path.dirname(__file__)))
        cls.test_conf_path = \
            os.path.join(basedir, "etc", "agent.conf")
        cls.conf_obj = config.AgentConfig([cls.test_conf_path])

        cls.bucket_name = "agentfetchtest" + str(uuid.uuid4()).split("-")[0]

        cls.conn = boto.connect_s3(
            os.environ[test_utils.S3_ACCESS_KEY_ENV],
            os.environ[test_utils.S3_SECRET_KEY_ENV])
        cls.bucket = cls.conn.create_bucket(cls.bucket_name)

    @classmethod
    def tearDownClass(cls):
        if test_utils.S3_ACCESS_KEY_ENV not in os.environ or test_utils.S3_SECRET_KEY_ENV not in os.environ:
            return

        try:
            all_keys = cls.bucket.get_all_keys()
            cls.bucket.delete_keys([k.name for k in all_keys])
            cls.bucket.delete()
        except Exception as ex:
            logging.exception("failed to clean up")
            raise

    def test_file_run(self):
        msg = str(uuid.uuid4())
        _, tmpfilepath = tempfile.mkstemp()
        _, exefile = tempfile.mkstemp()
        bash_script = """#!/bin/bash
echo $1 > %s
""" % tmpfilepath

        with open(exefile, "w") as fptr:
            fptr.write(bash_script)

        sha256 = hashlib.sha256()
        sha256.update(bash_script)
        actual_checksum = sha256.hexdigest()

        url = "file://%s" % exefile
        # we are now setup for the test
        arguments = {'url': url, 'arguments': [msg],
                     'checksum': actual_checksum}
        plugin = fetch_plugin.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "fetch_plugin", arguments)
        result = plugin.run()
        self.assertEqual(result['return_code'], 0)
        self.assertTrue(os.path.exists(tmpfilepath))

        with open(tmpfilepath, "r") as fptr:
            data = fptr.read().strip()

        self.assertEqual(data, msg)


    @test_utils.aws_access_needed
    def test_good_fetch_run(self):
        msg = str(uuid.uuid4())
        _, tmpfilepath = tempfile.mkstemp()
        bash_script = """#!/bin/bash
echo $1 > %s
""" % tmpfilepath

        sha256 = hashlib.sha256()
        sha256.update(bash_script)
        actual_checksum = sha256.hexdigest()

        key_name = "fetchtestkey" + str(uuid.uuid4()).split("-")[0]

        k = boto.s3.key.Key(self.bucket)
        k.key = key_name
        k.set_contents_from_string(bash_script, policy='public-read')
        k.make_public()
        url = "http://%s.s3.amazonaws.com/%s" % (self.bucket_name, key_name)
        # we are now setup for the test
        arguments = {'url': url, 'arguments': [msg],
                     'checksum': actual_checksum}
        plugin = fetch_plugin.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "fetch_plugin", arguments)
        result = plugin.run()
        self.assertEqual(result['return_code'], 0)
        self.assertTrue(os.path.exists(tmpfilepath))

        with open(tmpfilepath, "r") as fptr:
            data = fptr.read().strip()

        self.assertEqual(data, msg)

    @test_utils.aws_access_needed
    def test_bad_url(self):
        url = "http://nothere.dell.com/%s" % str(uuid.uuid4())
        # we are now setup for the test
        arguments = {'url': url}
        plugin = fetch_plugin.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "fetch_plugin", arguments)
        result = plugin.run()
        self.assertNotEqual(result['return_code'], 0)

    @test_utils.aws_access_needed
    def test_bad_checksum(self):
        msg = str(uuid.uuid4())
        _, tmpfilepath = tempfile.mkstemp()
        bash_script = """#!/bin/bash
echo $1 > %s
""" % tmpfilepath

        sha256 = hashlib.sha256()
        # fake a checksum for failure
        sha256.update(str(uuid.uuid4()))
        actual_checksum = sha256.hexdigest()

        key_name = "fetchtestkey" + str(uuid.uuid4()).split("-")[0]

        k = boto.s3.key.Key(self.bucket)
        k.key = key_name
        k.set_contents_from_string(bash_script, policy='public-read')
        k.make_public()
        url = "http://%s.s3.amazonaws.com/%s" % (self.bucket_name, key_name)
        # we are now setup for the test
        arguments = {'url': url, 'arguments': [msg],
                     'checksum': actual_checksum}
        plugin = fetch_plugin.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "fetch_plugin", arguments)
        self.assertRaises(exceptions.AgentPluginOperationException,
                          plugin.run)


class TestRunScriptPlugin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        basedir = os.path.dirname((os.path.dirname(__file__)))
        cls.test_conf_path = \
            os.path.join(basedir, "etc", "agent.conf")
        cls.conf_obj = config.AgentConfig([cls.test_conf_path])

    def test_python_run(self):
        py_script = """import sys
print sys.executable
"""
        b64_py = base64.b64encode(py_script)

        sha256 = hashlib.sha256()
        # fake a checksum for failure
        sha256.update(py_script)
        actual_checksum = sha256.hexdigest()


        arguments = {'b64script': b64_py, 'inpython': True, 'checksum': actual_checksum}
        plugin = run_script_plugin.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "run_script", arguments)
        result = plugin.run()
        self.assertEqual(result['return_code'], 0)
        self.assertEqual(sys.executable, result['message'].strip())

    def test_script_run(self):
        msg = str(uuid.uuid4())
        _, tmpfilepath = tempfile.mkstemp()
        bash_script = """#!/bin/bash
echo $1 > %s
""" % tmpfilepath

        sha256 = hashlib.sha256()
        sha256.update(bash_script)
        actual_checksum = sha256.hexdigest()

        b64_script = base64.b64encode(bash_script)

        arguments = {'b64script': b64_script, 'checksum': actual_checksum,
                     'arguments': [msg]}

        plugin = run_script_plugin.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "run_script", arguments)
        result = plugin.run()
        self.assertEqual(result['return_code'], 0)
        self.assertTrue(os.path.exists(tmpfilepath))

        with open(tmpfilepath, "r") as fptr:
            data = fptr.read().strip()

        self.assertEqual(data, msg)

    def test_script_run_bad_checksum(self):
        msg = str(uuid.uuid4())
        _, tmpfilepath = tempfile.mkstemp()
        bash_script = """#!/bin/bash
echo $1 > %s
""" % tmpfilepath

        sha256 = hashlib.sha256()
        sha256.update(str(uuid.uuid4()))
        actual_checksum = sha256.hexdigest()

        b64_script = base64.b64encode(bash_script)

        arguments = {'b64script': b64_script, 'checksum': actual_checksum,
                     'arguments': [msg]}

        plugin = run_script_plugin.load_plugin(
            self.conf_obj, str(uuid.uuid4()),
            {}, "run_script", arguments)
        self.assertRaises(exceptions.AgentPluginOperationException,
                          plugin.run)
