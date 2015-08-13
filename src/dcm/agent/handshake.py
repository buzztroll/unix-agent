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
import random
import string
import uuid

import dcm.agent
import dcm.agent.exceptions as exceptions
import dcm.agent.plugins.loader as plugin_loader

_g_logger = logging.getLogger(__name__)


def get_plugin_handshake_descriptor(conf):
    items = plugin_loader.get_all_plugins(conf)
    command_name_list = [i for i in items]
    return command_name_list


class HandshakeIncomingReply:
    DEFAULT_FORCE_BACKOFF = 60.0

    REPLY_CODE_SUCCESS = 200
    REPLY_CODE_BAD_TOKEN = 409
    REPLY_CODE_UNAUTHORIZED = 401
    REPLY_CODE_FORCE_BACKOFF = 503

    REPLY_KEY_FORCE_BACKOFF = "FORCE_BACKOFF"

    def __init__(self, reply_type, force_backoff=None,
                 agent_id=None, cloud_id=None, customer_id=None,
                 region_id=None, zone_id=None, server_id=None,
                 server_name=None, mount_point=None, pk=None,
                 dcm_version=None, cloud_delegate=None):
        self.reply_type = reply_type
        self.force_backoff = force_backoff
        self.agent_id = agent_id
        self.cloud_id = cloud_id
        self.customer_id = customer_id
        self.region_id = region_id
        self.zone_id = zone_id
        self.server_id = server_id
        self.server_name = server_name
        self.mount_point = mount_point
        self.pk = pk
        self.dcm_version = dcm_version
        self.cloud_delegate = cloud_delegate


class HandshakeManager(object):

    def __init__(self, conf, db):

        self.agent_id = None
        self.conf = conf
        self._db = db
        self._token_file_path = self.validate_token_file()
        self._token = None
        self._incoming_handshake_payload = None
        self._hs_doc = None
        if os.path.exists(self._token_file_path):
            try:
                with open(self._token_file_path, "r") as fptr:
                    self._token = fptr.readline().strip()
            except BaseException:
                _g_logger.exception("Failed to read the token file %s"
                                    % self._token_file_path)
        if self._token is None:
            self._generate_token()
        _g_logger.debug("TOKEN IS " + self._token)
        if 'FOR_TEST_AGENT_ID_ENV' in os.environ:
            self.agent_id = os.environ['FOR_TEST_AGENT_ID_ENV']


    def validate_token_file(self):
        token_dir = self.conf.get_secure_dir()
        # At some point we should validate that only this user can read this
        # file
        # utils.validate_file_permissions(
        #     token_dir, username=self.conf.system_user, permissions=0700)
        #
        token_file_path = os.path.join(token_dir, "token")
        return token_file_path

    def _generate_token(self):
        with os.fdopen(os.open(self._token_file_path,
                       os.O_WRONLY | os.O_CREAT,
                       int("0600", 8)), "w") as fptr:
            l = 30 + random.randint(0, 29)
            self._token = ''.join(random.choice(string.ascii_letters +
                                                string.digits +
                                                "-_!@#^(),.=+")
                                  for _ in range(l)) + str(uuid.uuid4())
            fptr.write(self._token)

    def incoming_document(self, incoming_doc):
        if incoming_doc['return_code'] == HandshakeIncomingReply.REPLY_CODE_SUCCESS:
            # this means that everything worked out well and we can move on
            payload = incoming_doc["handshake"]
            self._incoming_handshake_payload = payload

            self.agent_id = payload.get('agentID')
            customer_id = payload.get('customerId')

            # this next line should be a noop all but the first time
            self._db.check_agent_id(self.agent_id)
            self.conf.agent_id = self.agent_id
            self.conf.customer_id = customer_id

            hs = HandshakeIncomingReply(
                reply_type=HandshakeIncomingReply.REPLY_CODE_SUCCESS,
                mount_point=payload.get('mountPoint'),
                pk=payload.get('pk'),
                dcm_version=payload.get('version'),
                cloud_delegate=payload.get('cloudDelegate'),
                agent_id=self.agent_id,
                cloud_id=payload.get('cloudId'),
                customer_id=customer_id,
                region_id=payload.get('regionId'),
                zone_id=payload.get('zoneId'),
                server_id=payload.get('serverId'),
                server_name=payload.get('serverName'))
        elif incoming_doc['return_code'] ==\
                HandshakeIncomingReply.REPLY_CODE_BAD_TOKEN:
            # This signals that we used a bad token but have the chance to
            # recover by trying a new one
            self._generate_token()
            hs = HandshakeIncomingReply(HandshakeIncomingReply.REPLY_CODE_BAD_TOKEN)
        elif incoming_doc['return_code'] ==\
                HandshakeIncomingReply.REPLY_CODE_UNAUTHORIZED:
            # unauthorized, like anything else can be transient.  Sometimes
            # dcm is just not ready for the agent when it comes up
            hs = HandshakeIncomingReply(HandshakeIncomingReply.REPLY_CODE_UNAUTHORIZED)
        elif incoming_doc['return_code'] ==\
                HandshakeIncomingReply.REPLY_CODE_FORCE_BACKOFF:
            try:
                backoff = incoming_doc[HandshakeIncomingReply.REPLY_KEY_FORCE_BACKOFF]
            except KeyError:
                backoff = HandshakeIncomingReply.DEFAULT_FORCE_BACKOFF
            hs = HandshakeIncomingReply(
                HandshakeIncomingReply.REPLY_CODE_FORCE_BACKOFF,
                force_backoff=backoff)
        else:
            raise exceptions.AgentHandshakeUnknownTypeException(
                "Unknown exception type")
        self._hs_doc = hs
        return hs

    def get_send_document(self):
        plugin_dict = plugin_loader.get_all_plugins(self.conf)
        features = self.conf.features.copy()
        for plugin_name in plugin_dict:
            p_feature = plugin_loader.get_module_features(
                self.conf, plugin_name, plugin_dict[plugin_name])
            features.update(p_feature)

        features['plugins'] = get_plugin_handshake_descriptor(self.conf)
        meta_data_object = self.conf.meta_data_object
        ipv4s = meta_data_object.get_handshake_ip_address()
        ipv6s = []
        injected_id = meta_data_object.get_injected_id()
        vm_instance = meta_data_object.get_instance_id()

        handshake_doc = {
            'ipv4': ipv4s,
            'ipv6': ipv6s,
            'agent_id': self.agent_id,
            'token': self._token,
            'vm_instance': vm_instance,
            'injected_id': injected_id,
            'version': dcm.agent.g_version,
            'protocol_version': dcm.agent.g_protocol_version,
            'platform': self.conf.platform_name,
            'platform_version': self.conf.platform_version,
            'features': features
        }
        return handshake_doc
