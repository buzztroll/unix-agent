import logging
import os
import time

import dcm.agent.intrusion_detection.interface as id_iface


_g_logger = logging.getLogger(__name__)


class OssecIntrusion(id_iface.AgentIntrusionDetection):
    def __init__(self, conf, log_alert):
        self._conf = conf
        self._log_alert = None
        self._last_alert = 0
        self._alert_prefix = "** Alert"
        self._log_alert = log_alert
        self._open()
        self._file_time = os.stat(self._conf.intrusion_file).st_mtime

    def check(self):
        try:
            ft = os.stat(self._conf.intrusion_file).st_mtime
            if ft > self._file_time:
                self._send_alerts()
        except Exception as ex:
            _g_logger.exception(ex.message)

    def close(self):
        pass

    def _open(self):
        if not os.path.exists(self._conf.intrusion_file):
            msg = ("No intrusion detection system is currently installed on "
                   "this server. enStratus strongly recommends the "
                   "installation and use of an intrusion detection system in "
                   "your cloud computing infrastructure.")
            self._log_alert.alert(
                4, int(time.time() * 1000), "IDS Not Installed", msg)
            return

    def _parse_line(self, line):
        la = line.split()
        line_id = la[2]
        line_id = line_id[:-1]
        id_a = line_id.split(".")
        seconds = id_a[0]
        if len(id_a[1]) > 3:
            id_a[1] = id_a[1][0:3]
        millis = id_a[1]
        tm_ms = (seconds * 1000) + millis
        return tm_ms

    def _send_alerts(self):
        if not os.path.exists(self._conf.intrusion_file):
            return

        done = False
        with open(self._conf.intrusion_file, "r") as fptr:
            while done:
                line = fptr.readline()
                line = line.strip()
                if not line:
                    continue

                if not line.startswith(self._alert_prefix):
                    continue

                tm = self._parse_line(line)
                if tm < self._last_alert:
                    continue

                message = ""
                level = 1
                subject = None
                found = False
                line = fptr.readline()
                while line:
                    found = True
                    line = line.strip()
                    message = message + line
                    if line.startswith("Rule"):
                        pa = line.split
                        level = int(pa[3][:-1])
                        pa = line.split("->")
                        subject = pa[1].strip()
                    line = fptr.readline()

                if not found:
                    return

                if level < 6:
                    level = 0
                elif level == 7:
                    level = 3
                elif level == 8:
                    level = 4
                elif level == 9 or level == 10:
                    level = 5
                elif level < 16:
                    level -= 5
                else:
                    level = 10

                if level > 0:
                    if subject is None:
                        subject = "IDS ALERT"
                    else:
                        subject = "IDS ALERT: " + subject
                    self._log_alert.alert(level, tm, subject, message)

                self._last_alert = tm

    def start(self):
        pass

    def stop(self):
        pass


def load_plugin(conf, alert_sender):
    return OssecIntrusion(conf, alert_sender)
