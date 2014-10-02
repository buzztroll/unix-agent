#  ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================
import datetime
import json
import logging
import threading

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.orm.exc as orm_exc
from dcm.agent import exceptions
import dcm.agent.messaging.utils as messaging_utils
import dcm.agent.messaging.states as messaging_states


g_metadata = sqlalchemy.MetaData()
g_logger = logging.getLogger(__name__)


request_table = sqlalchemy.Table(
    'requests', g_metadata,
    sqlalchemy.Column('request_id', sqlalchemy.String(64), primary_key=True),
    sqlalchemy.Column('creation_time', sqlalchemy.types.TIMESTAMP(),
                      default=datetime.datetime.now()),
    sqlalchemy.Column('request_doc', sqlalchemy.Text),
    sqlalchemy.Column('reply_doc', sqlalchemy.Text),
    sqlalchemy.Column('state', sqlalchemy.String(32)),
    sqlalchemy.Column('agent_id', sqlalchemy.String(64)),
    sqlalchemy.Column('last_update_time', sqlalchemy.types.TIMESTAMP()),
    )


def fail_started_state(db_record):
    db_record.state = messaging_states.ReplyStates.REPLY
    r = {
        'Exception': "The job was executed but the state of the execution "
                     "was lost.",
        'return_code': 1}
    db_record.reply_doc = json.dumps(r)
    db_record.last_update_time = datetime.datetime.now()


class RequestDBObject(object):

    def __init__(self, request_id, incoming_document, agent_id, state,
                 reply_doc=None):
        self.request_doc = incoming_document
        self.reply_doc = reply_doc
        self.request_id = request_id
        self.state = state
        self.last_update_time = datetime.datetime.now()
        self.agent_id = agent_id


class RequestObject(object):

    # this is the disconnected object
    def __init__(self, connected_obj):
        self.request_doc = connected_obj.request_doc
        self.reply_doc = connected_obj.reply_doc
        self.request_id = connected_obj.request_id
        self.state = connected_obj.state
        self.last_update_time = datetime.datetime.now()
        self.agent_id = connected_obj.agent_id


sqlalchemy.orm.mapper(RequestDBObject, request_table)


def class_method_session(func):
    def wrapper(self, *args, **kwargs):
        session = self._get_session()
        try:
            kwargs['session'] = session
            rc = func(self, *args, **kwargs)
            session.commit()
            return rc
        except:
            session.rollback()
            raise
        finally:
            session.close()
    return wrapper


class AgentDB(object):

    def __init__(self, db_file):
        if db_file == ":memory:":
            dburl = "sqlite://"
        else:
            dburl = "sqlite:///%s" % db_file
        self._engine = sqlalchemy.create_engine(dburl)
        g_metadata.create_all(self._engine)

        self._session_factory = sqlalchemy.orm.sessionmaker(bind=self._engine)
        self._Session = sqlalchemy.orm.scoped_session(self._session_factory)
        self._Session = self._session_factory
        self._lock = threading.RLock()

    def _get_session(self):
        return self._Session()

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    @messaging_utils.class_method_sync
    @class_method_session
    def starting_agent(self, session=None):
        self._clear_all_lost(session)

    def _clear_all_lost(self, session):
        # load every object
        # in this step we decide that we cannot recover an job that has not
        # been known to reply.  If in the future we feel we can re-run jobs
        # safe then changes will need to be made here
        started_requests = session.query(RequestDBObject).filter(
            RequestDBObject.state==messaging_states.ReplyStates.ACKED).all()
        for req in started_requests:
            fail_started_state(req)
            session.add(req)

    @messaging_utils.class_method_sync
    @class_method_session
    def check_agent_id(self, agent_id, session=None):
        session.query(RequestDBObject).filter(
            RequestDBObject.agent_id != agent_id).delete()

    @messaging_utils.class_method_sync
    @class_method_session
    def get_all_complete(self, session=None):
        # load every object
        complete_tasks = session.query(RequestDBObject).filter(
            RequestDBObject.state==messaging_states.ReplyStates.REPLY_ACKED).\
            all()
        external_tasks = [RequestObject(i) for i in complete_tasks]
        return external_tasks

    @messaging_utils.class_method_sync
    @class_method_session
    def get_all_rejected(self, session=None):
        # load every object
        complete_tasks = session.query(RequestDBObject).filter(
            RequestDBObject.state==messaging_states.ReplyStates.NACKED).\
            all()
        external_tasks = [RequestObject(i) for i in complete_tasks]
        return external_tasks

    @messaging_utils.class_method_sync
    @class_method_session
    def get_all_reply_nacked(self, session=None):
        # load every object
        complete_tasks = session.query(RequestDBObject).filter(
            RequestDBObject.state==messaging_states.ReplyStates.REPLY_NACKED).\
            all()
        external_tasks = [RequestObject(i) for i in complete_tasks]
        return external_tasks

    @messaging_utils.class_method_sync
    @class_method_session
    def get_all_ack(self, session=None):
        # load every object
        complete_tasks = session.query(RequestDBObject).filter(
            RequestDBObject.state==messaging_states.ReplyStates.ACKED).all()
        external_tasks = [RequestObject(i) for i in complete_tasks]
        return external_tasks

    @messaging_utils.class_method_sync
    @class_method_session
    def get_all_reply(self, session=None):
        # load every object
        re_inflate_tasks = session.query(RequestDBObject).filter(
            RequestDBObject.state==messaging_states.ReplyStates.REPLY).all()
        external_tasks = [RequestObject(i) for i in re_inflate_tasks]
        return external_tasks

    @messaging_utils.class_method_sync
    @class_method_session
    def lookup_req(self, request_id, session=None):
        try:
            record = session.query(RequestDBObject).filter(
                RequestDBObject.request_id==request_id).one()
            return RequestObject(record)
        except orm_exc.NoResultFound:
            return None

    @messaging_utils.class_method_sync
    @class_method_session
    def new_record(self, request_id, request_doc, reply_doc, state, agent_id, session=None):
        req_doc_str = json.dumps(request_doc)

        db_obj = RequestDBObject(request_doc['request_id'],
                                 req_doc_str, agent_id, state)
        if reply_doc:
            db_obj.reply_doc = json.dumps(reply_doc)
        session.add(db_obj)

    @messaging_utils.class_method_sync
    @class_method_session
    def update_record(self, request_id, state, reply_doc=None, session=None):
        try:
            record = session.query(RequestDBObject).filter(
                RequestDBObject.request_id==request_id).one()
        except orm_exc.NoResultFound as ex:
            raise exceptions.PersistenceException(
                "The record %s was not found" % request_id)
        record.state = state
        if reply_doc is not None:
            try:
                reply_doc_str = json.dumps(reply_doc)
            except Exception as ex:
                g_logger.exception("cannot encode reply " + str(reply_doc))
                raise
            record.reply_doc = reply_doc_str
        session.add(record)

    @messaging_utils.class_method_sync
    @class_method_session
    def clean_all_expired(self, cut_off_time, session=None):
        try:
            recs = session.query(RequestDBObject).filter(
                RequestDBObject.last_update_time < cut_off_time).all()
        except orm_exc.NoResultFound:
            return
        for rec in recs:
            session.delete(rec)


class DBCleaner(threading.Thread):

    def __init__(self, db, max_time, max_size, interval):
        super(DBCleaner, self).__init__()
        self._max_time = max_time
        self.max_size = max_size
        self._interval = interval
        self._done = threading.Event()
        self._cond = threading.Condition()
        self._db = db

    def run(self):
        while not self._done.isSet():
            self._cond.acquire()
            try:
                self._cond.wait(self._interval)
                cut_off_time = datetime.datetime.now() - datetime.timedelta(
                    microseconds=self._max_time)
                self._db.clean_all_expired(cut_off_time)
            except Exception as ex:
                g_logger.exception("An exception occurred in the db sweeper "
                                   "thread " + ex.message)
            finally:
                self._cond.release()

    def done(self):
        self._cond.acquire()
        try:
            self._done.set()
            self._cond.notify()
        finally:
            self._cond.release()
