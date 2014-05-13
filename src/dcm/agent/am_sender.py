import datetime


class LogAlert(object):

    def __init__(self, conn):
        self._conn = conn

    def log(self, message):
        msg = {
            "type": "LOG",
            "message": message
        }
        self._conn.send(msg)

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
