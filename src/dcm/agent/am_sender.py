import datetime


class LogAlert(object):

    def __init__(self, conf, conn):
        self._conf = conf
        self._conn = conn

    def alert(self, tm, level, subject, message):
        nw = datetime.datetime.now()
        msg = {
            "type": "ALERT",
            "level": level,
            "subject": subject,
            "message": message,
            "alert_timestamp": tm,
            "current_timestamp": nw,
            "token": self._conf.token,
            "server_id": self._conf.server_id
        }
        self._conn.send(msg)
