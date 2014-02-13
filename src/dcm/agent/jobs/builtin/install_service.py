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

import dcm.agent.jobs.direct_pass as direct_pass
from dcm.agent import storagecloud


class InstallService(direct_pass.DirectPass):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InstallService, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        service_dir = \
            self.conf.get_service_directory(self.arguments["serviceId"])

        try:
            os.makedirs(service_dir)
        except OSError as osEx:
            if osEx.errno != 17:
                raise Exception("There was an error creating the directory "
                                "%s" % service_dir)

        object_name = self.arguments["serviceImageFile"]
        service_image_path = os.path.join(service_dir, object_name)
        if os.path.exists(service_image_path):
            os.remove(service_image_path)
            # TODO HANDLE ERRORS

        access_key = self.arguments["storageAccessKey"]
        secret_key = self.arguments["storageSecretKey"]
        container_name = self.arguments["serviceImageDirectory"]
        cloud_id = self.arguments["fromCloudId"]
        service_id = self.arguments["serviceId"]

        # there are two version that we have to deal with.  Instead of
        # switching on a version number we inspect the document for values
        delegate = self.arguments.get("deletegate", None)
        endpoint = self.arguments.get("endpoint", None)
        account = self.arguments.get("account", None)
        region_id = self.arguments.get("providerRegionId", self.conf.region_id)

        customer_id = self.arguments["customerId"]
        run_as_user = self.arguments["runAsUser"]

        storagecloud.download(
            cloud_id, container_name, object_name,
            access_key, secret_key,
            service_image_path,
            region_id=region_id,
            delegate=delegate,
            endpoint=endpoint,
            account=account)

        self.ordered_param_list = [service_id,
                                   customer_id,
                                   run_as_user,
                                   service_image_path]
        return super(InstallService, self).run()


def load_plugin(conf, job_id, items_map, name, arguments):
    return InstallService(conf, job_id, items_map, name, arguments)
