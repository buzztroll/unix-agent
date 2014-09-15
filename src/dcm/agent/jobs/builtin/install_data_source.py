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

import dcm.agent.jobs.direct_pass as direct_pass
from dcm.agent import storagecloud, utils


class InstallDataSource(direct_pass.DirectPass):

    protocol_arguments = {
        "customerId":
        ("The ID of the customer invoking the command.", True, str, None),
        "serviceId":
        ("The service ID for which this data source is being installed.",
         True, str, None),
        "imageDirectory":
        ("The directory or bucket that is holding the data in the storage "
         "cloud.", True, str, None),
        "dataSourceImage":
        ("The name of the data source image.", True, str, None),
        "cloudId":
        ("The ID or delegate of the cloud holding the data.", True, str, None),
        "apiAccessKey":
        ("The cloud API access key.", True, utils.base64type_convertor, None),
        "apiSecretKey":
        ("The cloud API secret key.", True, utils.base64type_convertor, None),
        "configuration":
        ("The configuration data used to install the data source.  This "
         "is written to a file and passed to the installer script.",
         True, utils.base64type_convertor, None),
        "regionId":
        ("The cloud region ID that is holding the data.", False, str, None),
        "apiEndpoint":
        ("The cloud API endpoint contact string.", False, str, None),
        "apiAccount":
        ("The cloud account.", False, str, None),
        "storageDelegate":
        ("For clouds that have a separate storage cloud contact, this "
         "value servers as the cloud ID", False, str, None),
        "storageEndpoint":
        ("The separate storage cloud endpoint contact string.",
         False, str, None),
        "storageAccount":
        ("The separate storage cloud account.", False, str, None),
        "storagePublicKey":
        ("The separate storage cloud API access key.",
         False, utils.base64type_convertor, None),
        "storagePrivateKey":
        ("The separate storage cloud API secret key.",
         False, utils.base64type_convertor, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InstallDataSource, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        service_id = self.args.serviceId
        object_name = self.args.dataSourceImage
        container_name = self.args.imageDirectory
        configuration = self.args.configuration

        endpoint = self.args.apiEndpoint
        account = self.args.apiAccount
        cloud_id = self.args.cloudId
        access_key = self.args.apiAccessKey
        secret_key = self.args.apiSecretKey
        region_id = self.arguments.get("regionId", self.conf.region_id)

        if "storageDelegate" in self.arguments:
            endpoint = self.args.storageEndpoint
            account = self.args.storageAccount
            cloud_id = self.args.storageDelegate
            region_id = self.arguments.get("regionId", self.conf.region_id)
            access_key = self.args.storagePublicKey
            secret_key = self.args.storagePrivateKey

        conf_file = self.conf.get_temp_file("installds.cfg")
        restore_file = self.conf.get_temp_file(object_name)
        try:
            with open(conf_file, "w") as fptr:
                fptr.write(configuration)

            storagecloud.download(
                cloud_id,
                container_name,
                object_name,
                access_key,
                secret_key,
                restore_file,
                region_id=region_id,
                endpoint=endpoint,
                account=account)

            self.ordered_param_list = [service_id,
                                       conf_file,
                                       restore_file]

            self.cwd = self.conf.get_service_directory(service_id)
            return super(InstallDataSource, self).run()
        finally:
            utils.safe_delete(conf_file)
            utils.safe_delete(restore_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return InstallDataSource(conf, job_id, items_map, name, arguments)
