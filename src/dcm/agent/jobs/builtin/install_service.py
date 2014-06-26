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
import os

import dcm.agent.jobs.direct_pass as direct_pass
from dcm.agent import storagecloud, exceptions, utils


_g_logger = logging.getLogger(__name__)


class InstallService(direct_pass.DirectPass):

    protocol_arguments = {
        "customerId":
        ("The ID of the customer invoking the command.", True, long),
        "serviceId":
        ("The ID of the service to be installed.", True, str),
        "runAsUser":
        ("The unix account name of the user that will run the install.",
         True, str),
        "cloudId":
        ("The ID of the cloud from which to download the service image.",
         True, str),
        "apiAccessKey":
        ("The access key for the cloud storing the service image.",
         True, utils.base64type_convertor),
        "apiSecretKey":
        ("The secret key for the cloud storing the service image.",
         True, utils.base64type_convertor),
        "serviceImageDirectory":
        ("The directory or bucket in the storage cloud that is holding"
         "the service image file.", True, str),
        "serviceImageFile":
        ("The name of the service image.", True, str),
        "providerRegionId":
        ("The region ID of the storage cloud holding the image.",
         False, str),
        "apiEndpoint":
        ("The endpoint contact string of the storage cloud.", False, str),
        "apiAccount":
        ("The storage cloud account.", False, str),
        "storageEndpoint":
        ("The separate storage cloud endpoint contact string.",
         False, str),
        "storageAccount":
        ("The separate storage cloud account information.", False, str),
        "storageAccessKey":
        ("The separate storage cloud API key.",
         False, utils.base64type_convertor),
        "storageSecretKey":
        ("The separate storage cloud secret key.",
         False, utils.base64type_convertor),
        "storageDelegate":
        ("For clouds that have separate contact information for their "
         "storage clouds this servers as the cloud ID.", False, str)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InstallService, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        if not os.path.exists(self.conf.storage_services_dir):
            raise exceptions.AgentPluginOperationException(
                "The services directory does not exist.  The agent is not "
                "properly configured.")

        service_dir = self.conf.get_service_directory(self.args.serviceId)
        try:
            os.makedirs(service_dir)
        except OSError as osEx:
            if osEx.errno != 17:
                raise Exception("There was an error creating the directory "
                                "%s" % service_dir)

        object_name = self.arguments["serviceImageFile"]
        container_name = self.arguments["serviceImageDirectory"]
        service_image_path = os.path.join(service_dir, object_name)
        if os.path.exists(service_image_path):
            _g_logger.warn("The service directory already existed for service"
                           " id %s." % self.args.serviceId)
            os.remove(service_image_path)
            # TODO HANDLE ERRORS

        cloud_id = self.args.cloudId
        access_key = self.args.apiAccessKey
        secret_key = self.args.apiSecretKey
        region_id = self.args.providerRegionId
        endpoint = self.args.apiEndpoint
        account = self.args.apiAccount

        if self.args.storageDelegate:
            endpoint = self.args.storageEndpoint
            account = self.args.storageAccount
            access_key = self.args.storageAccessKey
            secret_key = self.args.storageSecretKey
            cloud_id = self.args.storageDelegate

        if not region_id:
            region_id = self.conf.region_id

        try:
            storagecloud.download(
                cloud_id,
                container_name,
                object_name,
                access_key,
                secret_key,
                service_image_path,
                region_id=region_id,
                endpoint=endpoint,
                account=account)

            self.cwd = os.path.dirname(service_image_path)
            self.ordered_param_list = [self.args.serviceId,
                                       str(self.args.customerId),
                                       self.args.runAsUser,
                                       service_image_path]
            return super(InstallService, self).run()
        finally:
            utils.safe_delete(service_image_path)


def load_plugin(conf, job_id, items_map, name, arguments):
    return InstallService(conf, job_id, items_map, name, arguments)
