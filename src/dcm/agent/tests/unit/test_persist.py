import json
import unittest
import uuid
import datetime
import nose
import time

from dcm.agent import exceptions
from dcm.agent.messaging import persistence
import dcm.agent.messaging.states as messaging_states


class TestPersist(unittest.TestCase):

    def setUp(self):
        self.db = persistence.AgentDB(":memory:")

    def test_complete_empty(self):
        res = self.db.get_all_complete()
        nose.tools.eq_(res, [])

    def test_rejected_empty(self):
        res = self.db.get_all_rejected()
        nose.tools.eq_(res, [])

    def test_nacked_empty(self):
        res = self.db.get_all_reply_nacked()
        nose.tools.eq_(res, [])

    def test_acked_empty(self):
        res = self.db.get_all_ack()
        nose.tools.eq_(res, [])

    def test_reply_empty(self):
        res = self.db.get_all_reply()
        nose.tools.eq_(res, [])

    def test_lookup_empty(self):
        res = self.db.lookup_req("NotTThere")
        nose.tools.ok_(res is None)

    def test_update_not_there(self):
        passed = False
        try:
            self.db.update_record("Nope", "ASTATE")
        except exceptions.PersistenceException:
            passed = True
        nose.tools.ok_(passed)

    def test_new_record_ack_search(self):
        request_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        request_doc = {"request_id": request_id}
        state = messaging_states.ReplyStates.ACKED
        self.db.new_record(request_id, request_doc, None, state, agent_id)
        res = self.db.get_all_ack()
        nose.tools.ok_(res)
        nose.tools.eq_(len(res), 1)
        nose.tools.eq_(res[0].agent_id, agent_id)
        nose.tools.eq_(res[0].request_id, request_id)

    def test_new_record_reply_search(self):
        request_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        request_doc = {"request_id": request_id}
        state = messaging_states.ReplyStates.REPLY
        self.db.new_record(request_id, request_doc, None, state, agent_id)
        res = self.db.get_all_reply()
        nose.tools.ok_(res)
        nose.tools.eq_(len(res), 1)
        nose.tools.eq_(res[0].agent_id, agent_id)
        nose.tools.eq_(res[0].request_id, request_id)

    def test_new_record_reply_nacked_search(self):
        request_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        request_doc = {"request_id": request_id}
        state = messaging_states.ReplyStates.REPLY_NACKED
        self.db.new_record(request_id, request_doc, None, state, agent_id)
        res = self.db.get_all_reply_nacked()
        nose.tools.ok_(res)
        nose.tools.eq_(len(res), 1)
        nose.tools.eq_(res[0].agent_id, agent_id)
        nose.tools.eq_(res[0].request_id, request_id)

    def test_new_record_nacked_search(self):
        request_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        request_doc = {"request_id": request_id}
        state = messaging_states.ReplyStates.NACKED
        self.db.new_record(request_id, request_doc, None, state, agent_id)
        res = self.db.get_all_rejected()
        nose.tools.ok_(res)
        nose.tools.eq_(len(res), 1)
        nose.tools.eq_(res[0].agent_id, agent_id)
        nose.tools.eq_(res[0].request_id, request_id)

    def test_new_record_lookup(self):
        request_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        request_doc = {"request_id": request_id}
        state = messaging_states.ReplyStates.REPLY_NACKED
        reply_doc = {"akey": "andstuff"}

        self.db.new_record(request_id, request_doc, reply_doc, state, agent_id)
        res = self.db.lookup_req(request_id)
        nose.tools.eq_(res.agent_id, agent_id)
        nose.tools.eq_(res.request_id, request_id)
        nose.tools.eq_(json.loads(res.reply_doc), reply_doc)

    def test_new_record_update_lookup(self):
        request_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        request_doc = {"request_id": request_id}
        state = messaging_states.ReplyStates.REPLY_NACKED
        reply_doc = {"akey": "andstuff"}

        self.db.new_record(request_id, request_doc, None, state, agent_id)

        state = messaging_states.ReplyStates.ACKED
        self.db.update_record(request_id, state, reply_doc=reply_doc)

        res = self.db.lookup_req(request_id)
        nose.tools.eq_(res.agent_id, agent_id)
        nose.tools.eq_(res.request_id, request_id)
        nose.tools.eq_(json.loads(res.reply_doc), reply_doc)
        nose.tools.eq_(res.state, state)

    def test_clear_lost(self):
        request_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        request_doc = {"request_id": request_id}
        state = messaging_states.ReplyStates.ACKED
        reply_doc = {"akey": "andstuff"}

        self.db.new_record(request_id, request_doc, reply_doc, state, agent_id)

        self.db.starting_agent()
        res = self.db.lookup_req(request_id)
        nose.tools.eq_(res.agent_id, agent_id)
        nose.tools.eq_(res.request_id, request_id)
        r = json.loads(res.reply_doc)
        nose.tools.eq_(r["return_code"], 1)
        nose.tools.eq_(res.state, messaging_states.ReplyStates.REPLY)

    def test_clear_empty(self):
        cut_off_time = datetime.datetime.now()
        self.db.clean_all_expired(cut_off_time)

    def test_clear_lost(self):
        request_id1 = str(uuid.uuid4())
        request_id2 = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        request_doc = {"request_id": request_id1}
        state = messaging_states.ReplyStates.ACKED
        reply_doc = {"akey": "andstuff"}

        self.db.new_record(request_id1, request_doc, reply_doc, state, agent_id)

        time.sleep(0.1)
        cut_off_time = datetime.datetime.now()

        request_doc = {"request_id": request_id2}
        self.db.new_record(request_id2, request_doc, reply_doc, state, agent_id)

        self.db.clean_all_expired(cut_off_time)

        res = self.db.lookup_req(request_id1)
        nose.tools.ok_(res is None)
        res = self.db.lookup_req(request_id2)
        nose.tools.ok_(res is not None)


