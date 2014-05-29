import importlib
import logging
import time


_g_logger = logging.getLogger(__name__)


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


def setup_intrusion_detection(conf, conn):
    if not conf.intrusion_module:
        return

    _g_logger.info("Attempting to load the intrusion detection "
                   "module %s" % conf.intrusion_module)

    try:
        id_module = importlib.import_module(conf.intrusion_module)
        _g_logger.debug("ID module acquired " + str(dir(id_module)))
        alert_sender = AlertSender(conn)
        return id_module.load_plugin(conf, alert_sender)
    except Exception as ex:
        _g_logger.error("The module named %s could not be loaded", ex)
        return None
