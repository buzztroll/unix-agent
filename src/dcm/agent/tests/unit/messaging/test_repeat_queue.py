#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
