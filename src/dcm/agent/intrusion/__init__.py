import logging
import threading
import time
from dcm.agent import exceptions
from dcm.agent.intrusion import ossec


_g_logger = logging.getLogger(__name__)

logging.StreamHandler
class IntrusionRunner(threading.Thread):

    def __init__(self, conf):
        self._conf = conf
        self._exit = threading.Event()
        if not conf.intrusion_enabled:
            return
        if conf.intrusion_type != "ossec":
            raise exceptions.AgentOptionValueException(
                "[intrusion]type", conf.intrusion_type, ["ossec"])
        self._intrusion_obj = ossec.OssecIntrusion(conf)
        self.start()

    def run(self):
        while not self._exit.is_set():
            try:
                self._intrusion_obj.check()
                time.sleep(1.0)
            except Exception as ex:
                _g_logger.exception("Intrusion detection system error")

    def stop(self):
        self._exit.set()