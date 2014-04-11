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

import os
from dcm.agent import exceptions
import dcm.agent.utils as utils
import dcm.agent.jobs.direct_pass as direct_pass


class ImageServer(direct_pass.DirectPass):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ImageServer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):

        cert_file_name = self.conf.get_temp_file("cert.pem")
        pk_file_name = self.conf.get_temp_file("pk.pem")

        self.set_imaging(True)
        try:
            with open(cert_file_name, "w") as fptr:
                fptr.write(self.arguments["storageCertificate"])
            with open(pk_file_name, "w") as fptr:
                fptr.write(self.arguments["storagePrivateKey"])
            build_dir = self.conf.get_temp_file(
                "bundle-%s" % self.arguments["imageName"], isdir=True)

            self.ordered_param_list = [self.conf.customer_id,
                                       self.arguments["serverId"],
                                       self.arguments["imageDirectory"],
                                       self.arguments["imageName"],
                                       self.arguments["type"],
                                       self.arguments["accountNumber"],
                                       build_dir,
                                       self.arguments["cloudAccessKey"],
                                       self.arguments["cloudSecretKey"],
                                       cert_file_name,
                                       pk_file_name]
            tries = 0
            done = False
            while not done:
                tries = tries + 1
                try:
                    reply = super(ImageServer, self).run()
                    if reply["return_code"] == 0:
                        done = True
                    elif tries == self.conf.image_server_retrys_max:
                        return reply
                except Exception as ex:
                    if tries == self.conf.image_server_retrys_max:
                        raise exceptions.AgentPluginOperationException(
                            "We were unable to image the server after %d "
                            "tries" % tries, ex)

            # TODO if we get here the imaging was successful.  upload file
        finally:
            self.set_imaging(False)
            if os.path.exists(cert_file_name):
                os.remove(cert_file_name)
            if os.path.exists(pk_file_name):
                os.remove(pk_file_name)

    def set_imaging(self, b):
        # TODO make this do something under lock with config
        pass

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return ImageServer(conf, job_id, items_map, name, arguments)
