#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import os
import sys

import dcm.agent.exceptions as exceptions


_g_logger = logging.getLogger(__name__)


class RequesterEvents(object):
    REQUEST_MADE = "REQUEST_MADE"
    TIMEOUT = "TIMEOUT"
    ACK_RECEIVED = "ACK"
    REPLY_RECEIVED = "REPLY"
    NACK_RECEIVED = "NACK"
    CANCEL_REQUESTED = "CANCEL"
    CALLBACK_RETURNED = "CALLBACK"
    CLEANUP_TIMEOUT = "CLEANUP_TIMEOUT"


class RequesterStates(object):
    REQUEST_NEW = "NEW"
    REQUESTING = "REQUESTING"
    REQUESTED = "REQUESTED"
    REQUEST_FAILING = "REQUEST_FAILING"
    USER_CALLBACK = "USER_CALLBACK"
    SENDING_ACK = "SENDING_ACK"
    ACK_SENT = "ACK_SENT"
    CLEANUP = "CLEANUP"


class ReplyEvents(object):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    REPLY_ACK_RECEIVED = "REPLY_ACK"
    REPLY_NACK_RECEIVED = "REPLY_NACK"
    CANCEL_RECEIVED = "CANCEL"
    STATUS_RECEIVED = "STATUS"
    USER_ACCEPTS_REQUEST = "ACCEPTED"
    USER_REJECTS_REQUEST = "REJECTED"
    USER_REPLIES = "USER_REPLIES"
    DB_INFLATE = "DB_INFLATE"
    TIMEOUT = "TIMEOUT"


class ReplyStates(object):
    NEW = "NEW"
    REQUESTING = "REQUESTING"
    CANCEL_RECEIVED_REQUESTING = "CANCEL_RECEIVED_REQUESTING"
    ACKED = "ACKED"
    REPLY = "REPLY"
    NACKED = "NACKED"
    REPLY_NACKED = "REPLY_NACKED"
    REPLY_ACKED = "REPLY_ACKED"
