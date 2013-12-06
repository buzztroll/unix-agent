import json
import os
import unittest
import StringIO
from dcm.agent import dispatcher

import dcm.agent.config as config
from dcm.agent.messaging import types
import dcm.agent.messaging.reply as reply
import dcm.agent.tests.utils.test_connection as test_conn
import dcm.agent.tests.utils as test_utils


class TestSingleCommands(unittest.TestCase):

    def setUp(self):
        self.conf_obj = config.AgentConfig()
        test_conf_path = test_utils.get_conf_file()
        self.conf_obj.setup(conffile=test_conf_path)
        self.disp = dispatcher.Dispatcher(self.conf_obj)
        self.disp.start_workers()

    def tearDown(self):
        self.disp.stop()

    def _get_conn(self, incoming_lines, outfile, drop_count):
        self._incoming_io = StringIO.StringIO(incoming_lines)
        return test_conn.TestReplySuccessfullyAlways(
            incoming_lines, outfile, reply_ignore_count=drop_count)

    def _simple_message(self, drop_count, command, stdout, stderr):
        inlines = StringIO.StringIO(command)
        outfile = StringIO.StringIO()
        conn = self._get_conn(inlines, outfile, drop_count)
        request_listener = reply.RequestListener(conn, self.disp)

        # wait until the request is done
        while request_listener.is_busy() or \
                        request_listener.get_messages_processed() != 1:
            request_listener.poll()
        output = json.loads(outfile.buflist[0])
        self.assertEquals(stdout, output['stdout'].strip())
        self.assertEquals(stderr, output['stderr'])
        self.assertEquals(0, output['returncode'])

    def test_message_no_fail(self):
        self._simple_message(0, "echo Hello1", "Hello1", None)

    def test_message_drop_1_ack(self):
        self._simple_message(1, "echo Hello1", "Hello1", None)

    def test_message_drop_3_acks(self):
        self._simple_message(3, "echo Hello1", "Hello1", None)

    def test_long_message_no_fail(self):
        self._simple_message(0, "sleep 3", "", None)

    def test_long_message_drop_1_ack(self):
        self._simple_message(1, "sleep 3", "", None)

    def test_long_message_drop_3_ack(self):
        self._simple_message(3, "sleep 3", "", None)

    def test_short_sleep_message_no_fail(self):
        self._simple_message(0, "sleep 3", "", None)

    def test_short_sleep_message_drop_1_ack(self):
        self._simple_message(1, "sleep 0.1", "", None)

    def test_short_sleep_message_drop_3_ack(self):
        self._simple_message(3, "sleep 0.1", "", None)


class TestSerialCommands(unittest.TestCase):

    def setUp(self):
        self.conf_obj = config.AgentConfig()
        test_conf_path = test_utils.get_conf_file()
        self.conf_obj.setup(conffile=test_conf_path)
        self.disp = dispatcher.Dispatcher(self.conf_obj)
        self.disp.start_workers()

    def tearDown(self):
        self.disp.stop()

    def _get_conn(self, incoming_lines, outfile, drop_count):
        self._incoming_io = StringIO.StringIO(incoming_lines)
        return test_conn.TestReplySuccessfullyAlways(
            incoming_lines, outfile, reply_ignore_count=drop_count)

    def _many_message(self, count, drop_count, command):
        if type(command) == list:
            in_command = os.linesep.join(command)
            count = len(command)
        else:
            in_command = ""
            for i in range(count):
                in_command = in_command + command + os.linesep

        inlines = StringIO.StringIO(in_command)
        outfile = StringIO.StringIO()
        conn = self._get_conn(inlines, outfile, drop_count)
        request_listener = reply.RequestListener(conn, self.disp)

        # wait until the request is done
        while request_listener.is_busy() or \
            request_listener.get_messages_processed() != count:
            request_listener.poll()

        for i in range(count):
            output = json.loads(outfile.buflist[i])
            self.assertEquals(0, output['returncode'])

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
        self.conf_obj = config.AgentConfig()
        test_conf_path = test_utils.get_conf_file()
        self.conf_obj.setup(conffile=test_conf_path)
        self.disp = dispatcher.Dispatcher(self.conf_obj)
        self.disp.start_workers()

    def tearDown(self):
        self.disp.stop()

    def _get_conn(self, incoming_lines, outfile, drop_count, retrans_list):
        self._incoming_io = StringIO.StringIO(incoming_lines)
        conn = test_conn.TestReplySuccessfullyAlways(
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

        in_command = os.linesep.join(command)
        count = len(command)
        inlines = StringIO.StringIO(in_command)
        outfile = StringIO.StringIO()
        conn = self._get_conn(inlines, outfile, drop_count, retrans_list)
        request_listener = reply.RequestListener(conn, self.disp)
        to = TestStateObserver()
        rol = request_listener.get_reply_observers()
        rol.insert(0, to)

        # wait until the request is done
        while request_listener.is_busy() or \
            request_listener.get_messages_processed() != count:
            request_listener.poll()

        for i in range(count):
            output = json.loads(outfile.buflist[i])
            self.assertEquals(0, output['returncode'])

        return to.state_change_list

    def test_retrans_long(self):
        events = [
            types.MessageTypes.REQUEST,
            types.MessageTypes.ACK,
            types.MessageTypes.NACK,
            types.MessageTypes.REPLY,
            "AFTER_REPLY_ACK"
        ]
        for event in events:
            retrans = test_conn.RequestRetransmission()
            retrans.set_retrans_event(event, 1)
            self._many_message(0, ["sleep 0.5"], [retrans])

    def test_retrans_after_request_long(self):
        retrans = test_conn.RequestRetransmission()
        retrans.set_retrans_event(types.MessageTypes.REQUEST, 1)
        to = self._many_message(0, ["sleep 0.5"], [retrans])
        # verify that 2 requests were sent.  The second request
        # comes after the ack
        events = [i[0] for i in to]
        events.remove('REQUEST_RECEIVED')
        events.remove('REQUEST_RECEIVED')

    def test_retrans_after_ack_long(self):
        retrans = test_conn.RequestRetransmission()
        retrans.set_retrans_event(types.MessageTypes.ACK, 1)
        to = self._many_message(0, ["sleep 0.5"], [retrans])

        expected = [('REQUEST_RECEIVED', 'NEW', 'REQUESTING'),
                    ('ACCEPTED', 'REQUESTING', 'ACKED'),
                    ('REQUEST_RECEIVED', 'ACKED', 'ACKED'),
                    ('USER_REPLIES', 'ACKED', 'REPLY'),
                    ('REPLY_ACK', 'REPLY', 'CLEANUP')]
        self.assertEqual(to, expected)

    def test_retrans_after_reply_long(self):
        retrans = test_conn.RequestRetransmission()
        retrans.set_retrans_event(types.MessageTypes.REPLY, 1)
        to = self._many_message(0, ["sleep 0.5"], [retrans])

    def test_retrans_after_reply_ack_long(self):
        retrans = test_conn.RequestRetransmission()
        retrans.set_retrans_event("AFTER_REPLY_ACK", 1)
        to = self._many_message(0, ["sleep 0.5"], [retrans])
