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
import os
import sqlite3
import threading

import dcm.agent.exceptions as exceptions
import dcm.agent.messaging.states as messaging_states
import dcm.agent.utils as agent_utils


_g_logger = logging.getLogger(__name__)


_g_sqllite_ddl = """
create table if not exists requests (
    request_id        TEXT primary key not null,
    creation_time     date,
    request_doc       text,
    reply_doc         text,
    state             string,
    agent_id          string,
    last_update_time  date
);
"""


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


def _get_column_order():
    return ["request_id", "creation_time", "request_doc",
            "reply_doc", "state", "agent_id", "last_update_time"]


class SQLiteRequestObject(object):

    # this is the disconnected object
    def __init__(self, row):
        if row is None:
            raise exceptions.PersistenceException("The row is none")
        column_order = _get_column_order()
        i = 0
        for attr in column_order:
            setattr(self, attr, row[i])
            i += 1


class SQLiteAgentDB(object):

    def __init__(self, db_file):
        self._db_file = db_file
        self._lock = threading.RLock()

        try:
            self._db_conn = sqlite3.connect(
                self._db_file, check_same_thread=False)
            try:
                self._db_conn.executescript(_g_sqllite_ddl)
                self._db_conn.commit()
            except Exception as ex:
                _g_logger.exception(
                    "Could not open " + db_file + " " + str(ex))
                self._db_conn.rollback()
                raise
        except Exception as ex:
            _g_logger.exception(
                "Could not connect to the DB " + db_file + " " + str(ex))
            raise

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def _log_db_info(self):
        if os.path.exists(self._db_file):
            st = os.stat(self._db_file)
            msg = "DB: " + self._db_file + os.linesep + str(st)
        else:
            msg = "DB: " + self._db_file + " does not exist."
        _g_logger.warn(msg)

    def _execute(self, func):
        try:
            cursor = self._db_conn.cursor()
            try:
                rc = func(cursor)
                self._db_conn.commit()
                return rc
            except Exception as ex:
                _g_logger.exception(
                    "Could not access " + self._db_file + " " + str(ex))
                self._db_conn.rollback()
                raise
            finally:
                cursor.close()
        except Exception as ex:
            _g_logger.exception(
                "Failed to access the DB " + self._db_file + " " + str(ex))
            self._log_db_info()
            raise

    @agent_utils.class_method_sync
    def starting_agent(self):
        r = {
            'Exception':
            "The job was executed but the state of the execution was lost.",
            'return_code': 1}
        reply_doc = json.dumps(r)

        stmt = ("UPDATE requests SET state=?, reply_doc=? WHERE state=?")

        def do_it(cursor):
            cursor.execute(stmt,
                           (messaging_states.ReplyStates.REPLY,
                            reply_doc,
                            messaging_states.ReplyStates.ACKED))
        self._execute(do_it)

    @agent_utils.class_method_sync
    def check_agent_id(self, agent_id):
        stmt = 'DELETE FROM requests where agent_id <> ?'

        def do_it(cursor):
            cursor.execute(stmt, (agent_id,))
        self._execute(do_it)

    def _get_all_state(self, state):
        stmt = ("SELECT " + ", ".join(_get_column_order()) +
                " FROM requests WHERE state=\"" + state + '"')

        def do_it(cursor):
            cursor.execute(stmt)
            rows = cursor.fetchall()
            if not rows:
                return []
            return [SQLiteRequestObject(i) for i in rows]
        return self._execute(do_it)

    @agent_utils.class_method_sync
    def get_all_complete(self):
        return self._get_all_state(messaging_states.ReplyStates.REPLY_ACKED)

    @agent_utils.class_method_sync
    def get_all_rejected(self, session=None):
        return self._get_all_state(messaging_states.ReplyStates.NACKED)

    @agent_utils.class_method_sync
    def get_all_reply_nacked(self, session=None):
        return self._get_all_state(messaging_states.ReplyStates.REPLY_NACKED)

    @agent_utils.class_method_sync
    def get_all_ack(self):
        return self._get_all_state(messaging_states.ReplyStates.ACKED)

    @agent_utils.class_method_sync
    def get_all_reply(self):
        return self._get_all_state(messaging_states.ReplyStates.REPLY)

    @agent_utils.class_method_sync
    def lookup_req(self, request_id):
        stmt = ("SELECT " + ", ".join(_get_column_order()) + " FROM "
                'requests where request_id=?')

        def do_it(cursor):
            cursor.execute(stmt, [request_id])
            row = cursor.fetchone()
            if not row:
                return
            return SQLiteRequestObject(row)
        return self._execute(do_it)

    @agent_utils.class_method_sync
    def new_record(self, request_id, request_doc, reply_doc, state,
                   agent_id):
        stmt = ("INSERT INTO requests(request_id, creation_time, request_doc, "
                "reply_doc, state, agent_id, last_update_time) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)")

        if request_id != request_doc['request_id']:
            raise exceptions.PersistenceException("The request_id must match "
                                                  "the request_doc")

        if request_doc is not None:
            request_doc = json.dumps(request_doc)
        if reply_doc is not None:
            reply_doc = json.dumps(reply_doc)

        def do_it(cursor):
            nw = datetime.datetime.now()
            parms = (request_id, nw, request_doc,
                     reply_doc, state, agent_id, nw)
            cursor.execute(stmt, parms)
        self._execute(do_it)

    @agent_utils.class_method_sync
    def update_record(self, request_id, state, reply_doc=None):
        stmt = ("UPDATE requests SET state=?, reply_doc=?, last_update_time=? "
                "WHERE request_id=?")
        try:
            if reply_doc is not None:
                reply_doc = json.dumps(reply_doc)

            def do_it(cursor):
                nw = datetime.datetime.now()
                cursor.execute(stmt, (state, reply_doc, nw, request_id))
                if cursor.rowcount != 1:
                    raise exceptions.PersistenceException(
                        "%d rows were updated when exactly 1 should have "
                        "been" % cursor.rowcount)
            self._execute(do_it)
        except Exception as ex:
            raise exceptions.PersistenceException(ex)

    @agent_utils.class_method_sync
    def clean_all_expired(self, cut_off_time):
        stmt = ("DELETE FROM requests WHERE request_id in (SELECT request_id "
                "FROM requests WHERE last_update_time < ?)")

        def do_it(cursor):
            cursor.execute(stmt, (cut_off_time,))
        self._execute(do_it)

    @agent_utils.class_method_sync
    def clean_all(self, request_id):
        stmt = ("DELETE FROM requests WHERE request_id <> ?")
        def do_it(cursor):
            cursor.execute(stmt, (request_id,))
        self._execute(do_it)


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
                _g_logger.exception("An exception occurred in the db sweeper "
                                    "thread " + str(ex))
            finally:
                self._cond.release()

    def done(self):
        self._cond.acquire()
        try:
            self._done.set()
            self._cond.notify()
        finally:
            self._cond.release()
