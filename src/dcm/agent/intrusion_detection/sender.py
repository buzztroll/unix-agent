import time


class AlertSender(object):

    def __init__(self, conn):
        self._conn = conn

    def send_alert(self, level, alert_timestamp, subject, message):

        current_timestamp = int(round(time.time() * 1000))
        msg = {
            "type": "ALERT",
            "message": message,
            "subject": subject,
            "alert_timestamp": alert_timestamp,
            "current_timestamp": current_timestamp,
            "level": level
        }
        self._conn.send(msg)
