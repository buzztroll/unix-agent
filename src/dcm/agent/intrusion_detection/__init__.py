import importlib
import logging
import time
import uuid
from dcm.agent.messaging.alert_msg import AlertAckMsg


_g_logger = logging.getLogger(__name__)


class AlertSender(object):

    def __init__(self, conn):
        self._conn = conn
        self._alerts = {}

    def send_alert(self, level, alert_timestamp, subject, message):

        current_timestamp = int(round(time.time() * 1000))
        req_id = str(uuid.uuid4())
        msg = {
            "request_id": req_id,
            "type": "ALERT",
            "message": message,
            "subject": subject,
            "alert_timestamp": alert_timestamp,
            "current_timestamp": current_timestamp,
            "level": level
        }
        self._conn.send(msg)
        self._alerts[req_id] = AlertAckMsg(10.0, msg, self._conn)

    def incoming_message(self, message_doc):
        req_id = message_doc["request_id"]
        if req_id not in self._alerts:
            _g_logger.warn("The request_id %s was not found.  Retransmissions "
                           "could cause this" % req_id)
            return

        alert_ack = self._alerts[req_id]
        alert_ack.incoming_message(message_doc)
        del self._alerts[req_id]


class AlertManager(object):

    def __init__(self, a_conn, plugin):
        self._aconn = a_conn
        self._plugin = plugin

    def start(self):
        self._plugin.start()

    def stop(self):
        self._plugin.stop()

    def incoming_message(self, message_doc):
        self._aconn.incoming_message(message_doc)


def setup_intrusion_detection(conf, conn):
    if not conf.intrusion_module:
        return

    _g_logger.info("Attempting to load the intrusion detection "
                   "module %s" % conf.intrusion_module)

    try:
        id_module = importlib.import_module(conf.intrusion_module)
        _g_logger.debug("ID module acquired " + str(dir(id_module)))
        alert_sender = AlertSender(conn)
        plugin = id_module.load_plugin(conf, alert_sender)
        return AlertManager(alert_sender, plugin)
    except Exception as ex:
        _g_logger.error("The module named %s could not be loaded", ex)
        return None
