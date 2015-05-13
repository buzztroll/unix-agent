import unittest

import dcm.agent.connection.websocket as websocket


class TestRequesterStandardPath(unittest.TestCase):

    def test_basic_same(self):
        msg = "some message"
        q = websocket.RepeatQueue()
        q.put(msg)
        back = q.get()
        self.assertEqual(msg, back)

    def test_message_id_unique(self):
        msg = {'message_id': 'sdfsfsfsd'}
        q = websocket.RepeatQueue()
        q.put(msg)
        q.put(msg)

        count_back = 0
        while True:
            try:
                q.get(block=False)
                count_back += 1
            except Exception:
                break
        self.assertEqual(count_back, 1)

    def test_repeat_queue_too_many(self):
        msg = {'request_id': 'sdfsfsfsd'}
        max_id = 10
        q = websocket.RepeatQueue(max_req_id=max_id)

        for i in range(max_id*2):
            q.put(msg)

        count_back = 0
        while True:
            try:
                q.get(block=False)
                count_back += 1
            except Exception:
                break

        self.assertEqual(count_back, max_id)
