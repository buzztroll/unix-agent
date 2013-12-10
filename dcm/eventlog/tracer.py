import logging
import threading


_g_tl_key = "DCM_EVENT_THREAD_LOCAL_KEY"
_g_thread_local_stack = threading.local()
_g_event_log_set = ()
_g_event_logger = logging.getLogger(__name__)


def _get_record_defaults(doc):
    kw_str = ""
    delim = ""
    if "kwargs" in doc:
        kwargs = doc["kwargs"]
        for k in kwargs:
            kw_str = "%s%s%s=%s" % (kw_str, delim, k, str(kwargs[k]))
    record = {"dcm_kwargs": kw_str}
    key_words = ['request_id', 'message_type', 'command_name', 'plugin_name',
                 'tracer_id', 'message_id']
    for k in key_words:
        record["dcm_" + k] = doc.get(k, "None")
    return record

class RequestFilter(logging.Filter):
    """
    Fliter records if this event is not in the logset
    """
    def filter(self, record):
        if _g_event_log_set and record.levelno not in _g_event_log_set:
            # filter out the log if it is not in the level set
            return False

        if not hasattr(_g_thread_local_stack, _g_tl_key):
            # load up the record with default data
            rec = _get_record_defaults({})
            record.__dict__.update(rec)
            return True

        stack = getattr(_g_thread_local_stack, _g_tl_key, None)
        if not stack:
            rec = _get_record_defaults({})
            record.__dict__.update(rec)
            return True

        request_id_info = stack[-1]
        rec = _get_record_defaults(request_id_info)
        record.__dict__.update(rec)
        return True


class RequestTracer():
    def __init__(self, request_id, message_doc=None, command_name=None,
                 plugin_name=None, tracer_id=None, **kwargs):

        # set the initial stack value if it does not already exist in this
        # thread
        if not hasattr(_g_thread_local_stack, _g_tl_key):
            setattr(_g_thread_local_stack, _g_tl_key, [])
        record = {'request_id': request_id,
                  'kwargs': kwargs,
                  "plugin_name": plugin_name,
                  "command_name": command_name,
                  "tracer_id": tracer_id}
        if message_doc:
            record['message_type'] = message_doc['type']
            record['message_id'] = message_doc['message_id']
        self._record = record

    def __enter__(self):
        thread_stack = getattr(_g_thread_local_stack, _g_tl_key)
        thread_stack.append(self._record)
        _g_event_logger.log(1, "Setup new request tracer state.")

    def __exit__(self, type, value, traceback):
        thread_stack = getattr(_g_thread_local_stack, _g_tl_key)
        thread_stack.pop()
        _g_event_logger.log(1, "End request tracer state.")
        if value is not None:
            _g_event_logger.log(1, "Request context manager ended with an "
                                   "exception: %s." % value)
            # TODO log the traceback
