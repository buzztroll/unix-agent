#  ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================
import datetime
import json
import threading
from dcm.agent import exceptions
import dcm.agent.messaging.utils as utils


class JsonPage(object):
    def __init__(self, page_size, obj_list):
        self.creation_time = datetime.datetime.now()
        self._obj_list = obj_list
        self._page_size = page_size
        self._lock = threading.RLock()

    @utils.class_method_sync
    def get_next_page(self):
        page_list = []
        size_so_far = 0
        for json_obj in self._obj_list:
            line_size = len(json.dumps(json_obj))
            if size_so_far + line_size > self._page_size:
                break
            page_list.append(json_obj)
            size_so_far += line_size
        self._obj_list = self._obj_list[len(page_list):]
        return (page_list, len(self._obj_list))

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()


class PageMonitor(object):

    def __init__(self, page_size=12*1024, life_span=60*60*2, sweep_time=10):
        self._pages = {}
        self._page_size = page_size
        self._lock = threading.RLock()
        self._life_span = life_span
        self._timer = None
        self._stopped = False
        self._sweep_time = sweep_time

    def start(self):
        if self._stopped:
            return
        self._timer = threading.Timer(self._sweep_time, self.clean_sweep)
        self._timer.start()

    def stop(self):
        self._stopped = True
        if self._timer is not None:
            self._timer.cancel()

    @utils.class_method_sync
    def get_next_page(self, token):
        if token not in self._pages:
            raise exceptions.AgentPageNotFoundException(token)
        pager = self._pages[token]
        (page, remaining) = pager.get_next_page()
        if remaining < 1:
            del self._pages[token]
            token = None
        return page, token

    @utils.class_method_sync
    def new_json_page(self, json_list, token):
        pager = JsonPage(self._page_size, json_list)
        self._pages[token] = pager

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    @utils.class_method_sync
    def clean_sweep(self):
        too_old = datetime.datetime.now() - \
                  datetime.timedelta(seconds=self._life_span)
        kill_keys = []
        for k in self._pages:
            pager = self._pages[k]
            if pager.creation_time < too_old:
                kill_keys.append(k)
        for k in kill_keys:
            del self._pages[k]
        self.start()
