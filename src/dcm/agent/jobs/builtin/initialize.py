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

import logging

import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class InitializeJob(jobs.Plugin):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InitializeJob, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        # verify that the parameters in initialize match what came in on the
        # connection
        try:
            if self.arguments["cloudId"] != self.conf.cloud_id:
                raise Exception("cloud ID from initialize does not match "
                                "the original value received from the "
                                "connection handshake")
            if self.arguments["customerId"] != self.conf.customer_id:
                raise Exception("customer ID from initialize does not match "
                                "the original value received from the "
                                "connection handshake")
            if self.arguments["regionId"] != self.conf.region_id:
                raise Exception("region ID from initialize does not match "
                                "the original value received from the "
                                "connection handshake")
            if self.arguments["zoneId"] != self.conf.zone_id:
                raise Exception("zone ID from initialize does not match "
                                "the original value received from the "
                                "connection handshake")
            if self.arguments["serverId"] != self.conf.server_id:
                raise Exception("server ID from initialize does not match "
                                "the original value received from the "
                                "connection handshake")
            if self.arguments["serverName"] != self.conf.server_name:
                raise Exception("server name from initialize does not match "
                                "the original value received from the "
                                "connection handshake")
            if self.arguments["ephemeralFileSystem"] !=\
                    self.conf.ephemeral_file_system:
                raise Exception("ephemeralFileSystem from initialize does"
                                "not match "
                                "the original value received from the "
                                "connection handshake")
            if self.arguments["encryptedEphemeralFsKey"] !=\
                    self.conf.encrypted_ephemeral_fs_key:
                raise Exception("encryptedEphemeralFsKey from initialize does "
                                "not match "
                                "the original value received from the "
                                "connection handshake")

            # TODO WALK THE INTIT STEPS

        except Exception as ex:
            return {'return_code': 1, "message": ex.message}

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    _g_logger.debug("loading %s" % __name__)
    return InitializeJob(conf, job_id, items_map, name, arguments)
