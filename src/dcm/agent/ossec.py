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
import calendar
import logging
import os
import re
import threading
import time
import uuid

import dcm.agent.messaging.alert_msg as alert_msg

from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler


_g_logger = logging.getLogger(__name__)

# put this in global space so it is only compiled once
_g_rule_matcher = re.compile("Rule: (.*?) \(level (.*?)\) -> '(.*?)'")


class OssecAlert(object):
    def __init__(self, line):
        self.line_count = 0
        self.rule = None
        self.level = None
        self.subject = None
        self.message = ""
        la = line.split()
        self.timestamp = float(la[2][:-1])

    def input_line(self, line):
        if line.startswith("Rule:"):
            match = _g_rule_matcher.search(line)
            self.rule = match.group(1)
            self.level = match.group(1)
            self.subject = match.group(1)
        else:
            self.message = self.message + line


def parse_file(fname, cutofftime, sender):
    current_alert = None
    with open(fname, "r") as fptr:
        for line in fptr.readlines():
            if line.startswith('** Alert '):
                if current_alert is not None:
                    # right here is where a new event is ready to be sent
                    sender.send_alert(
                        new_alert.timestamp, new_alert.subject,
                        new_alert.level, new_alert.rule, new_alert.message)

                new_alert = OssecAlert(line)
                # skip anything that we have already processed
                if new_alert.timestamp < cutofftime:
                   current_alert = None
                else:
                    current_alert = new_alert
            else:
                if current_alert is not None:
                    current_alert.input_line(line)


class AlertSender(FileSystemEventHandler):

    def __init__(self, conn, db, poll_interval=5.0,
                 dir_to_watch="/opt/dcm-agent-extras/ossec/logs/alerts",
                 w_file="alerts.log"):
        super(FileSystemEventHandler, self).__init__()
        self._conn = conn
        self._db = db
        self._alerts = {}
        self._alert_by_hash = {}
        self._stopping = None
        self._thread = None
        self._cond = threading.Condition()
        self._poll_interval = poll_interval
        self._last_processed = time.time()
        self.dir_to_watch = dir_to_watch
        self.w_file = w_file
        self.observer = None

    def send_alert(self, alert_time, subject, level, rule, message):
        _g_logger.debug("Send alert request")
        request_id = str(uuid.uuid4())
        doc = {
            'type': 'ALERT',
            'request_id': request_id,
            'current_timestamp': calendar.timegm(time.gmtime()) * 1000,
            'alert_timestamp': int(float(alert_time) * 1000),
            'level': level,
            'rule': rule,
            'message': message,
            'subject': subject
        }

        alert = alert_msg.AlertAckMsg(doc, self._conn)
        if alert.alert_hash not in self._alert_by_hash:
            _g_logger.info("Sending alert " + str(doc))
            self._alerts[request_id] = alert
            self._alert_by_hash[alert.alert_hash] = alert
            alert.send()


    def incoming_message(self, incoming_doc):
        request_id = incoming_doc['request_id']
        alert = self._out_standing_alerts[request_id]
        alert.incoming_message()

        self._db.add_alert(alert.doc['alert_timestamp'],
                           alert.doc['current_timestamp'],
                           alert.alert_hash,
                           alert.doc['level'],
                           alert.doc['rule'],
                           alert.doc['subject'],
                           alert.doc['message'])
        del self._out_standing_alerts[request_id]
        del self._alert_by_hash[alert.alert_hash]

    def stop(self):
        _g_logger.debug("Stopping alert message sender")
        if self._stopping is None:
            logging.debug("Alert was not started")
            return
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        if self._thread is not None:
            self._cond.acquire()
            try:
                self._stopping.set()
                self._cond.notify()
            finally:
                self._cond.release()
            self._thread.join()

    def start(self):
        _g_logger.debug("Starting alert message sender %s" % self.dir_to_watch)
        if self._thread is not None:
            raise Exception("The alert object has already been started.")
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._run)
        self._thread.start()
        try:
            self.observer = Observer()
            self.observer.schedule(self, path=self.dir_to_watch)
            self.observer.start()
        except:
            self.observer = None
            raise

    def on_modified(self, event):
        self._process(event)

    def on_created(self, event):
        self._process(event)

    def _process(self, event):
        _g_logger.debug("A new watchdog event arrived %s" % str(event))
        if event.is_directory:
            _g_logger.debug("Skipping the watchdog directory event")
            return

        if not self.w_file in event.src_path:
            _g_logger.debug("Skipping the watchdog event %s" % event.src_path)
            return

        _g_logger.debug("Signal the runner that the event should be processed")
        self._cond.acquire()
        try:
            self._cond.notify()
        finally:
            self._cond.release()

    def _run(self):
        timeout = self._poll_interval
        self._cond.acquire()
        try:
            while not self._stopping.is_set():
                # do work here
                self._cond.wait(timeout=timeout)
                _g_logger.debug("ossec processor thread woke up")
                time_now = time.time()
                time_diff = time_now - self._last_processed
                if  time_diff < self._poll_interval:
                    timeout = self._poll_interval - time_diff
                else:
                    self._last_processed = time_now
                    timeout = None
                    latest_processed_time = self._db.get_latest_alert_time()
                    alert_file = os.path.join(self.dir_to_watch, self.w_file)
                    parse_file(alert_file, latest_processed_time, self)
        finally:
            self._cond.release()
