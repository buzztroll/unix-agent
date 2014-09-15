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
         True, str, None),
        "toBackupDirectory":
        ("The remote backup directory or bucket in the storage cloud where "
         "this backup will be uploaded.",
         True, str, None),
        "primaryCloudId":
        ("The cloud ID or delegate string of the primary storage cloud.",
         True, str, None),
        "primaryRegionId":
        ("The region ID for the primary storage cloud.",
         False, str, None),
        "primaryApiKey":
        ("The API key for the primary storage cloud.",
         True, utils.base64type_convertor, None),
        "primarySecretKey":
        ("The API secret key for the primary storage cloud.",
         True, utils.base64type_convertor, None),
        "secondaryCloudId":
        ("The cloud ID or delegate string for the secondary storage cloud. "
         "Often this is an off site cloud.",
         False, str, None),
        "secondaryRegionId":
        ("The region ID of the secondary cloud.",
         False, str, None),
        "secondaryApiKey":
        ("The API key of the secondary cloud.",
         False, utils.base64type_convertor, None),
        "secondarySecretKey":
        ("The API secret key of the secondary cloud.",
         False, utils.base64type_convertor, None),
        "apiEndpoint":
        ("The endpoint contact string of the primary cloud.",
         False, str, None),
        "apiAccount":
        ("The account string of the primary backup cloud.",
         False, str, None),
        "storageDelegate":
        ("When this value is set it overides the primary API information. "
         "When the primary cloud does not have a storage cloud this value "
         "is set to make user of an alternative cloud.",
         False, str, None),
        "storageEndpoint":
        ("The endpoint contact string of the separate primary cloud.",
         False, str, None),
        "storageAccount":
        ("The account string of the separate primary cloud.",
         False, str, None),
        "storagePublicKey":
        ("The API key for the separate primary storage cloud.",
         False, utils.base64type_convertor, None),
        "storagePrivateKey":
        ("The API secret key for the separate primary storage cloud.",
         False, utils.base64type_convertor, None),
        "secondaryApiEndpoint":
        ("The endpoint contact string of the secondary backup cloud.",
         False, str, None),
        "secondaryApiAccount":
        ("The account string of the secondary backup cloud.",
         False, str, None),
        "secondaryStorageDelegate":
        ("If a separate storage cloud is used for the secondary cloud this "
         "value will be set to the cloud ID or the storage delegate.",
         False, str, None),
        "secondaryStorageEndpoint":
        ("The endpoint contact string of the separate secondary storage "
         "clouds.",
         False, str, None),
        "secondaryStorageAccount":
        ("The account string of the separate secondary storage cloud.",
         False, str, None),
        "secondaryStoragePublicKey":
        ("The API key of the separate secondary storage cloud.",
         False, utils.base64type_convertor, None),
        "secondaryStoragePrivateKey":
        ("The API secret key for the separate secondary storage cloud.",
         False, utils.base64type_convertor, None)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(BackupService, self).__init__(
            conf, job_id, items_map, name, arguments)

        self.service_id = self.args.serviceId
        self.primary_cloud_id = self.args.primaryCloudId
        self.primary_region = self.args.primaryRegionId
        self.primary_api_key = self.args.primaryApiKey
        self.primary_secret_key = self.args.primarySecretKey
        self.primary_endpoint = self.args.apiEndpoint
        self.primary_account = self.args.apiAccount
        if "storageDelegate" in arguments:
            # if the storage delegate exists we will use it instead of the
            # primary info
            self.primary_cloud_id = self.args.storageDelegate
            self.primary_api_key = self.args.storagePublicKey
            self.primary_secret_key = self.args.storagePrivateKey
            self.primary_endpoint = self.args.storageEndpoint
            self.primary_account = self.args.storageAccount

        self.secondary_cloud_id = self.args.secondaryCloudId
        if self.secondary_cloud_id:
            self.secondary_region = self.args.secondaryRegionId
            self.secondary_api_key = self.args.secondaryApiKey
            self.secondary_secret_key = self.args.secondarySecretKey
            self.secondary_endpoint = self.args.secondaryApiEndpoint
            self.secondary_account = self.args.secondaryApiAccount

        if "secondaryStorageDelegate" in arguments:
            self.secondary_cloud_id = self.args.secondaryStorageDelegate
            self.secondary_region = self.args.secondaryRegionId
            self.secondary_api_key = self.args.secondaryStoragePublicKey
            self.secondary_secret_key = self.args.secondaryStoragePrivateKey
            self.secondary_endpoint = self.args.secondaryStorageEndpoint
            self.secondary_account = self.args.secondaryStorageAccount

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

        utils.log_to_dcm(
            logging.INFO, "Uploading %s to storage cloud %s" %
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
