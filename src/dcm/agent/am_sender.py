import datetime


class LogAlert(object):

    def __init__(self, conn):
        self._conn = conn

    def alert(self, tm, level, subject, message):
        nw = datetime.datetime.now()
        msg = {
            "type": "ALERT",
            "level": level,
            "subject": subject,
            "message": message,
            "alert_timestamp": tm,
            "current_timestamp": nw
        }
        self._conn.send(msg)
