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
from dcm.agent import exceptions, utils
import dcm.agent.jobs.direct_pass as direct_pass


class ImageServer(direct_pass.DirectPass):

    protocol_arguments = {
        "customerId":
        ("The ID of the customer running this command.",
         True, long),
        "serverId":
        ("This value is passed to the imageServer script but is never "
         "used",
         True, str),
        "accountNumber":
        ("The account number.  Used with EC2", True, str),
        "imageDirectory":
        ("This is passed to the imageServer script but is not used.",
         True, str),
        "imageName":
        ("The name of the image.", True, str),
        "type":
        ("The architecture of the image.", True, str),
        "cloudAccessKey":
        ("The access key for the cloud where the server is being imaged.",
         True, utils.base64type_convertor),
        "cloudSecretKey":
        ("The secret key for the cloud where the server is being imaged.",
         True, utils.base64type_convertor),
        "storageCertificate":
        ("The storage certificate.", True, utils.base64type_convertor),
        "storagePrivateKey":
        ("The storage private key.", True, utils.base64type_convertor)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(ImageServer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):

        if self.conf.is_imaging():
            raise exceptions.AgentPluginOperationException(
                "An outstanding image operation is in progress.")

        cert_file_name = self.conf.get_temp_file("cert.pem")
        pk_file_name = self.conf.get_temp_file("pk.pem")

        self.conf.set_imaging(True)
        try:
            with open(cert_file_name, "w") as fptr:
                fptr.write(
                    self.arguments["storageCertificate"].decode("utf-8"))
            with open(pk_file_name, "w") as fptr:
                fptr.write(self.arguments["storagePrivateKey"].decode("utf-8"))
            build_dir = self.conf.get_temp_file(
                "bundle-%s" % self.arguments["imageName"], isdir=True)

            self.ordered_param_list = [
                self.conf.customer_id,
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
            try:
                self._run_with_reties(self.conf.image_server_retrys_max)
            finally:
                self.conf.set_imaging(False)
            reply_str = self.upload_image(build_dir)
            reply = {"return_code": 0, "message": None,
                     "error_message": None, "return_type": "string",
                     "return_object": reply_str}
            return reply
        finally:
            if os.path.exists(cert_file_name):
                os.remove(cert_file_name)
            if os.path.exists(pk_file_name):
                os.remove(pk_file_name)

    def upload_image(self, build_dir):
        object_name = self.arguments["imageName"] + ".manifest.xml"

        local_path = os.path.join(build_dir, object_name)
        if not os.path.exists(local_path):
            raise exceptions.AgentPluginOperationException(
                "The local file %s was not created." % local_path)

        self.ordered_param_list = [self.arguments["imageDirectory"],
                                   local_path,
                                   self.arguments["cloudAccessKey"],
                                   self.arguments["cloudSecretKey"]]

        region_id = self.arguments.get("providerRegionId", self.conf.region_id)
        if region_id:
            self.ordered_param_list.append(region_id)
        self._run_with_reties(self.conf.image_server_retrys_max)
        return local_path

    def _run_with_reties(self, max_tries):
        tries = 0
        done = False
        while not done:
            tries = tries + 1
            try:
                reply = super(ImageServer, self).run()
                if reply["return_code"] == 0:
                    return reply
                else:
                    msg = reply["message"] + " || " + reply["error_message"]
                    raise Exception(msg)
            except Exception as ex:
                if tries == max_tries:
                    raise exceptions.AgentPluginOperationException(
                        "We were unable to image the server after %d "
                        "tries. %s" % (tries, ex.message))


def load_plugin(conf, job_id, items_map, name, arguments):
    return ImageServer(conf, job_id, items_map, name, arguments)
