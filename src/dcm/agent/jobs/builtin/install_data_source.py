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

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InstallDataSource, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        service_id = self.arguments["serviceId"]
        object_name = self.arguments["dataSourceImage"]
        container_name = self.arguments["imageDirectory"]
        cloud_id = self.arguments["fromCloudId"]
        access_key = self.arguments["storageAccessKey"]
        secret_key = self.arguments["storageSecretKey"]
        configuration = self.arguments["configuration"]
        delegate = self.arguments.get("deletegate", None)
        endpoint = self.arguments.get("endpoint", None)
        account = self.arguments.get("account", None)
        region_id = self.arguments.get("providerRegionId", self.conf.region_id)

        conf_file = self.conf.get_temp_file("installds.cfg")
        restore_file = self.conf.get_temp_file(object_name)
        try:
            with open(conf_file, "w") as fptr:
                fptr.write(configuration)

            storagecloud.download(
                cloud_id, container_name, object_name,
                access_key, secret_key,
                restore_file,
                region_id=region_id,
                delegate=delegate,
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
