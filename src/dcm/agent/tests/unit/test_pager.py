import json
import unittest
import time
from dcm.agent import exceptions

from src.dcm.agent.jobs import pages


class TestHandshake(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_walk_pager_uniform_sizes(self):
        json_entry = {"12345": "6789"}
        j_size = len(json.dumps(json_entry))
        per_page = 4
        page_size = per_page * j_size
        page_count = 5
        total_entries = per_page * page_count
        json_list = []

        for i in range(total_entries):
            json_list.append(json_entry)

        page_monitor = pages.PageMonitor(page_size=page_size)
        token = "applesauce"
        page_monitor.new_json_page(json_list, token)
        page_1, new_token = page_monitor.get_next_page(token)

        self.assertEqual(token, new_token)
        self.assertEqual(len(page_1), per_page)

        count = 1
        while new_token is not None:
            page, new_token = page_monitor.get_next_page(token)
            self.assertEqual(len(page), per_page)
            count += 1
        self.assertEqual(page_count, count)

    def tests_sweeper(self):
        json_entry = {"12345": "6789"}
        j_size = len(json.dumps(json_entry))
        per_page = 3
        page_size = per_page * j_size
        page_monitor = pages.PageMonitor(page_size=page_size, life_span=2, sweep_time=1)
        page_monitor.start()
        try:
            json_list = [json_entry, json_entry]
            token = "pudding"
            page_monitor.new_json_page(json_list, token)

            time.sleep(3)

            self.assertRaises(exceptions.AgentPageNotFoundException,
                              page_monitor.get_next_page,
                              token)
        finally:
            page_monitor.stop()

