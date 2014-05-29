import importlib
import logging

import dcm.agent.intrusion_detection.sender as id_sender


_g_logger = logging.getLogger(__name__)


def setup_intrusion_detection(conf, conn):
    if not conf.intrusion_module:
        return

    _g_logger.info("Attempting to load the intrusion detection "
                   "module %s" % conf.intrusion_module)

    try:
        id_module = importlib.import_module(conf.intrusion_module)
        _g_logger.debug("ID module acquired " + str(dir(id_module)))
        alert_sender = id_sender.AlertSender(conn)
        return id_module.load_plugin(conf, alert_sender)
    except Exception as ex:
        _g_logger.error("The module named %s could not be loaded", ex)
        return None


