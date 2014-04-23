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

from dcm.agent import exceptions, storagecloud
import dcm.agent.utils as utils
import dcm.agent.jobs.direct_pass as direct_pass


_g_logger = logging.getLogger(__name__)


class BackupService(direct_pass.DirectPass):

    protocol_arguments = {
        "serviceId":
        ("The ID of the service to be backed up.  The service script "
         "enstratus-backupService will be called.",
         True, str),
        "toBackupDirectory":
        ("The remote backup directory or bucket in the storage cloud where "
         "this backup will be uploaded.",
         True, str),
        "primaryCloudId":
        ("The cloud ID or delegate string of the primary storage cloud.",
         True, str),
        "primaryRegionId":
        ("The region ID for the primary storage cloud.",
         False, str),
        "primaryApiKey":
        ("The API key for the primary storage cloud.",
         True, str),
        "primarySecretKey":
        ("The API secret key for the primary storage cloud.",
         True, str),
        "secondaryCloudId":
        ("The cloud ID or delegate string for the secondary storage cloud. "
         "Often this is an off site cloud.",
         False, str),
        "secondaryRegionId":
        ("The region ID of the secondary cloud.",
         False, str),
        "secondaryApiKey":
        ("The API key of the secondary cloud.",
         False, str),
        "secondarySecretKey":
        ("The API secret key of the secondary cloud.",
         False, str),
        "apiEndpoint":
        ("The endpoint contact string of the primary cloud.",
         False, str),
        "apiAccount":
        ("The account string of the primary backup cloud.",
         False, str),
        "storageDelegate":
        ("When this value is set it overides the primary API information. "
         "When the primary cloud does not have a storage cloud this value "
         "is set to make user of an alternative cloud.",
         False, str),
        "storageEndpoint":
        ("The endpoint contact string of the separate primary cloud.",
         False, str),
        "storageAccount":
        ("The account string of the separate primary cloud.",
         False, str),
        "storagePublicKey":
        ("The API key for the separate primary storage cloud.",
         False, str),
        "storagePrivateKey":
        ("The API secret key for the separate primary storage cloud.",
         False, str),
        "secondaryApiEndpoint":
        ("The endpoint contact string of the secondary backup cloud.",
         False, str),
        "secondaryApiAccount":
        ("The account string of the secondary backup cloud.",
         False, str),
        "secondaryStorageDelegate":
        ("If a separate storage cloud is used for the secondary cloud this "
         "value will be set to the cloud ID or the storage delegate.",
         False, str),
        "secondaryStorageEndpoint":
        ("The endpoint contact string of the separate secondary storage "
         "clouds.",
         False, str),
        "secondaryStorageAccount":
        ("The account string of the separate secondary storage cloud.",
         False, str),
        "secondaryStoragePublicKey":
        ("The API key of the separate secondary storage cloud.",
         False, str),
        "secondaryStoragePrivateKey":
        ("The API secret key for the separate secondary storage cloud.",
         False, str)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(BackupService, self).__init__(
            conf, job_id, items_map, name, arguments)

        self.service_id = arguments["serviceId"]
        self.primary_cloud_id = arguments["primaryCloudId"]
        self.primary_region = arguments.get("primaryRegionId", None)
        self.primary_api_key = arguments["primaryApiKey"]
        self.primary_secret_key = arguments["primarySecretKey"]
        self.primary_endpoint = arguments.get("apiEndpoint", None)
        self.primary_account = arguments.get("apiAccount", None)
        if "storageDelegate" in arguments:
            # if the storage delegate exists we will use it instead of the
            # primary info
            self.primary_cloud_id = arguments["storageDelegate"]
            self.primary_api_key = arguments["storagePublicKey"]
            self.primary_secret_key = arguments["storagePrivateKey"]
            self.primary_endpoint = arguments.get("storageEndpoint", None)
            self.primary_account = arguments.get("storageAccount", None)

        self.secondary_cloud_id = arguments.get("secondaryCloudId", None)
        if self.secondary_cloud_id:
            self.secondary_region = arguments.get("secondaryRegionId", None)
            self.secondary_api_key = arguments["secondaryApiKey"]
            self.secondary_secret_key = arguments["secondarySecretKey"]
            self.secondary_endpoint = arguments.get(
                "secondaryApiEndpoint", None)
            self.secondary_account = arguments.get("secondaryApiAccount", None)

        if "secondaryStorageDelegate" in arguments:
            self.secondary_cloud_id = arguments["secondaryStorageDelegate"]
            self.secondary_region = None
            self.secondary_api_key = arguments["secondaryStoragePublicKey"]
            self.secondary_secret_key = arguments["secondaryStoragePrivateKey"]
            self.secondary_endpoint = arguments.get(
                "secondaryStorageEndpoint", None)
            self.secondary_account = arguments.get(
                "secondaryStorageAccount", None)

    def run(self):
        tm_str = utils.get_time_backup_string()
        backup_file_name = self.arguments["serviceId"] + "-" + tm_str
        backup_path = os.path.join(self.conf.storage_temppath,
                                   backup_file_name + ".zip")

        script_name = self.items_map["script_name"]
        command = [self.conf.get_script_location(script_name),
                   self.service_id,
                   backup_path]
        cwd = self.conf.get_service_directory(self.service_id)
        (stdout, stderr, rc) = utils.run_command(self.conf, command, cwd=cwd)
        if rc != 0:
            msg = "Unable to backup service to " + backup_path + ": " + \
                  rc + " | " + stderr
            _g_logger.warn(msg)
            raise exceptions.AgentJobException(msg)

        _g_logger.info("Uploading %s to storage cloud %s" %
                       (backup_path, self.primary_cloud_id))

        storagecloud.upload(
            self.primary_cloud_id,
            backup_path,
            self.arguments["toBackupDirectory"],
            backup_file_name,
            self.primary_api_key,
            self.primary_secret_key,
            region_id=self.primary_region,
            endpoint=self.primary_endpoint,
            account=self.primary_account)

        if self.secondary_cloud_id:
            storagecloud.upload(
                self.secondary_cloud_id,
                backup_path,
                self.arguments["toBackupDirectory"],
                backup_file_name,
                self.secondary_api_key,
                self.secondary_secret_key,
                region_id=self.secondary_region,
                endpoint=self.secondary_endpoint,
                account=self.secondary_account)

        reply = {"return_code": 0, "message": "",
                 "error_message": "", "return_type": "void"}
        return reply


def load_plugin(conf, job_id, items_map, name, arguments):
    return BackupService(conf, job_id, items_map, name, arguments)
