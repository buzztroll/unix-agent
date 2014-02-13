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
from dcm.agent import jobs
from dcm.agent.jobs import direct_pass

#forCustomerId, intoServiceId, fromImageDirectory, fromDataSourceImage,
#				fromCloudId, usingAccessKey, withSecretKey, encryption, encryptedWithStorageKey, basedOnPrivateStorageKey,
#				havingConfiguration
from dcm.agent import storagecloud


class InstallDataSource(jobs.Plugin):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(InstallDataSource, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        access_key = self.arguments["using_access_key"]
        secret_key = self.arguments["with_secret_key"]
        container_name = self.arguments["from_image_directory"]
        object_name = self.arguments["from_data_source_image"]

        dest_file = self.conf.get_temp_file(object_name)
        conf_file = self.conf.get_temp_file(object_name)

        storagecloud.download(self.conf, container_name, object_name,
             access_key, secret_key, dest_file)

        # write config data to temp file
        script_name = self.items_map["script_name"]
        exe_path = self.conf.get_script_location(script_name)

        cmd = [exe_path,
               self.arguments["into_service_id"],
               conf_file,
               dest_file]



    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return InstallDataSource(conf, job_id, items_map, name, arguments)
