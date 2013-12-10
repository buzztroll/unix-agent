import logging
import unittest
from dcm.eventlog import tracer


class TestEventTracer(unittest.TestCase):

    def test_basic_event_log(self):

        logger = logging.getLogger(__name__)
        filter = tracer.RequestFilter()
        logger.addFilter(filter)
        with tracer.RequestTracer("12345"):
            logger.error("A log record")

        pass


