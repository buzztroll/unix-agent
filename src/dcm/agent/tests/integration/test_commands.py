import json
import os
import shutil
import io
import tempfile
import unittest

import dcm.agent.config as config
import dcm.agent.dispatcher as dispatcher
import dcm.agent.logger as logger
import dcm.agent.messaging.persistence as persistence
import dcm.agent.messaging.reply as reply
import dcm.agent.messaging.types as types
import dcm.agent.tests.utils.test_connection as test_conn
import dcm.agent.tests.utils.general as test_utils
import dcm.agent.plugins.testplugins as testplugins
from dcm.agent.events.globals import global_space as dcm_events

testplugins.register_test_loader()


class TestSingleCommands(unittest.TestCase):

    def setUp(self):
        logger.clear_dcm_logging()
        test_conf_path = test_utils.get_conf_file()
        self.conf_obj = config.AgentConfig([test_conf_path])
        self.disp = dispatcher.Dispatcher(self.conf_obj)
        self.test_base_path = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_base_path, "agentdb.sql")
        self.db = persistence.SQLiteAgentDB(self.db_path)

    def tearDown(self):
        self.disp.stop()
        shutil.rmtree(self.test_base_path)

    def _get_conn(self, incoming_lines, outfile, drop_count):
        return test_conn.TestConnection(
            incoming_lines, outfile, reply_ignore_count=drop_count)

    def _simple_message(self, drop_count, command, stdout, stderr):
        inlines = io.StringIO(command)
        outfile = io.StringIO()
        conn = self._get_conn(inlines, outfile, drop_count)
        request_listener = reply.RequestListener(
            self.conf_obj, conn, self.disp, self.db)
        try:
            conn.set_receiver(request_listener)
            self.disp.start_workers(request_listener)

            # wait until the request is done
            while request_listener.get_messages_processed() != 1:
                dcm_events.poll()

            line = outfile.getvalue().split('\n')[0]
            line = line.strip()
            output = json.loads(line)
            self.assertEquals(stdout, output['message'].strip())
            self.assertEquals(stderr, output['error_message'])
            self.assertEquals(0, output['return_code'])
        finally:
            request_listener.shutdown()
            request_listener.wait_for_all_nicely()

    def test_message_no_fail(self):
        self._simple_message(0, "echo Hello1", "Hello1", '')

    def test_message_drop_1_ack(self):
        self._simple_message(1, "echo Hello1", "Hello1", '')

    def test_message_drop_3_acks(self):
        self._simple_message(3, "echo Hello1", "Hello1", '')

    def test_long_message_no_fail(self):
        self._simple_message(0, "sleep 3", "", '')

    def test_long_message_drop_1_ack(self):
        self._simple_message(1, "sleep 3", "", '')

    def test_long_message_drop_3_ack(self):
        self._simple_message(3, "sleep 3", "", '')

    def test_short_sleep_message_no_fail(self):
        self._simple_message(0, "sleep 3", "", '')

    def test_short_sleep_message_drop_1_ack(self):
        self._simple_message(1, "sleep 0.1", "", '')

    def test_short_sleep_message_drop_3_ack(self):
        self._simple_message(3, "sleep 0.1", "", '')


class TestSerialCommands(unittest.TestCase):

    def setUp(self):
        logger.clear_dcm_logging()
        test_conf_path = test_utils.get_conf_file()
        self.conf_obj = config.AgentConfig([test_conf_path])
        self.disp = dispatcher.Dispatcher(self.conf_obj)
        self.test_base_path = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_base_path, "agentdb.sql")
        self.db = persistence.SQLiteAgentDB(self.db_path)

    def tearDown(self):
        self.disp.stop()
        shutil.rmtree(self.test_base_path)

    def _get_conn(self, incoming_lines, outfile, drop_count):
        return test_conn.TestConnection(
            incoming_lines, outfile, reply_ignore_count=drop_count)

    def _many_message(self, count, drop_count, command):
        if type(command) == list:
            in_command = os.linesep.join(command)
            count = len(command)
        else:
            in_command = ""
            for i in range(count):
                in_command = in_command + command + os.linesep

        inlines = io.StringIO(in_command)
        outfile = io.StringIO()

        conn = self._get_conn(inlines, outfile, drop_count)
        request_listener = reply.RequestListener(
            self.conf_obj, conn, self.disp, self.db)
        conn.set_receiver(request_listener)
        self.disp.start_workers(request_listener)

        # wait until the request is done
        while request_listener.get_messages_processed() < count:
            dcm_events.poll()

            for line in outfile.getvalue().split('\n'):
                line = line.strip()
                if line:
                    output = json.loads(line.strip())
                    self.assertEquals(0, output['return_code'])

        request_listener.shutdown()
        request_listener.wait_for_all_nicely()

    def test_echo_serial_message_no_fail(self):
        self._many_message(2, 0, "echo hello")

    def test_echo_serial_message_failures(self):
        self._many_message(2, 3, "echo hello")

    def test_sleep_overlap(self):
        self._many_message(0, 0, ["sleep 5", "echo hello1", "sleep 3",
                                  "sleep 6", "echo hello2"])

    def test_sleep_overlap_many_failures(self):
        self._many_message(0, 10, ["sleep 5", "echo hello1", "sleep 3",
                                   "echo hello2"])


class TestRetransmission(unittest.TestCase):

    def setUp(self):
        logger.clear_dcm_logging()
        test_conf_path = test_utils.get_conf_file()
        self.conf_obj = config.AgentConfig([test_conf_path])
        self.test_base_path = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_base_path, "agentdb.db")
        self.db = persistence.SQLiteAgentDB(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.test_base_path)

    def _get_conn(self, incoming_lines, outfile, drop_count, retrans_list):
        conn = test_conn.TestConnection(
            incoming_lines, outfile, reply_ignore_count=drop_count,
            retrans_requests=retrans_list)
        return conn

    def _many_message(self, drop_count, command, retrans_list):
        class TestStateObserver(reply.ReplyObserverInterface):
            def new_message(self, reply):
                pass

            def message_done(self, reply):
                self.state_change_list = reply._sm.get_event_list()

            def incoming_message(self, incoming_doc):
                pass

        request_listener = None
        disp = dispatcher.Dispatcher(self.conf_obj)

        try:
            in_command = os.linesep.join(command)
            count = len(command)
            inlines = io.StringIO(in_command)
            outfile = io.StringIO()
            conn = self._get_conn(inlines, outfile, drop_count, retrans_list)

            request_listener = reply.RequestListener(
                self.conf_obj, conn, disp, self.db)
            conn.set_receiver(request_listener)
            to = TestStateObserver()
            rol = request_listener.get_reply_observers()
            rol.insert(0, to)
            disp.start_workers(request_listener)

            # wait until the request is done.  in the case of reply
            # retransmissions this value could be greater than count
            while request_listener.get_messages_processed() < count:
                dcm_events.poll()

            for line in outfile.getvalue().split('\n'):
                line = line.strip()
                if line:
                    output = json.loads(line.strip())
                    self.assertEquals(0, output['return_code'])
        finally:
            if request_listener:
                request_listener.shutdown()
                request_listener.wait_for_all_nicely()
            if disp:
                disp.stop()

        return to.state_change_list

    def test_retrans_long(self):
        events = [
            types.MessageTypes.REQUEST,
            types.MessageTypes.ACK,
            types.MessageTypes.NACK,
            types.MessageTypes.REPLY,
        ]
        for command in ["sleep 0.5", "echo hello"]:
            for event in events:
                retrans = test_conn.RequestRetransmission()
                retrans.set_retrans_event(event, 1)
                self._many_message(0, [command], [retrans])

    def test_retrans_after_request_long(self):
        retrans = test_conn.RequestRetransmission()
        retrans.set_retrans_event(types.MessageTypes.REQUEST, 1)
        to = self._many_message(0, ["sleep 0.5"], [retrans])
        # verify that 2 requests were sent.  The second request
        # comes after the ack
        events = [i[0] for i in to]
        events.remove('REQUEST_RECEIVED')

    def test_retrans_after_ack_long(self):
        retrans = test_conn.RequestRetransmission()
        retrans.set_retrans_event(types.MessageTypes.ACK, 1)

    def test_retrans_after_reply_long(self):
        retrans = test_conn.RequestRetransmission()
        retrans.set_retrans_event(types.MessageTypes.REPLY, 1)

    def test_retrans_overlap(self):
        events = [
            types.MessageTypes.REQUEST,
            types.MessageTypes.ACK,
            types.MessageTypes.NACK,
            types.MessageTypes.REPLY,
        ]
        for event in events:
            retrans = test_conn.RequestRetransmission()
            retrans.set_retrans_event(event, 1)
            self._many_message(0, ["sleep 0.5", "echo hello"],
                               [retrans])

    def test_many_retrans_overlap(self):
        events = [
            types.MessageTypes.REQUEST,
            types.MessageTypes.ACK,
            types.MessageTypes.NACK,
            types.MessageTypes.REPLY,
        ]
        retrans_list = []
        for event in events:
            retrans = test_conn.RequestRetransmission()
            retrans.set_retrans_event(event, 1)
            retrans_list.append(retrans)
        self._many_message(4, ["sleep 0.5", "echo hello", "sleep 0.1"],
                           retrans_list)
