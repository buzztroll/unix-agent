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
from dcm.agent import exceptions
import dcm.agent.utils as utils
import dcm.agent.jobs.direct_pass as direct_pass
from dcm.agent import storagecloud


_g_logger = logging.getLogger(__name__)


class BackupDataSource(direct_pass.DirectPass):

    protocol_arguments = {
        "serviceId": ("The ID of the service on which "
                      "enstratus-backupDataSource will be called", True, str),
        "dataSourceName": ("The name of the data source.  This value will be "
                           "passed to the enstratus-backupDataSource script. "
                           "It is the base name for the destination backup "
                           "file. Date information will be encoded into the "
                           "name.",
                           True, str),
        "toBackupDirectory": ("The remote directory or bucket name",
                              True, str),
        "primaryCloudId": ("The cloud ID or delegate string to which the "
                           "backup will be sent", True, str),
        "primaryRegionId": ("The region ID of the cloud where the backup "
                            "will be stored", False, str),
        "primaryApiKey": ("The API key for the backup cloud", True, str),
        "primarySecretKey": ("The API secret for the backup cloud", True, str),
        "configuration": ("The configuration data that will be passed to "
                          "enstratus-backupDataSource", True, str),
        "secondaryEndpoint": ("The endpoint for the off site account",
                              False, str),
        "secondaryAccount": ("The account for the off site cloud.",
                             False, str),
        "secondaryCloudId": ("The cloud ID for the secondary backup cloud",
                             False, str),
        "secondaryRegionId": ("The region ID for the secondary cloud",
                              False, str),
        "secondaryApiKey": ("The access key for the secondary cloud",
                            False, str),
        "secondarySecretKey": ("The secret API key for the secondary cloud",
                               False, str),
        "apiEndpoint": ("The endpoint contact string of the primary backup "
                        "cloud", False, str),
        "apiAccount": ("The API account of the primary backup cloud",
                       False, str),
        "storageDelegate": ("For clouds setups where a separate storage cloud "
                            "is used this value will be the cloud ID for that "
                            "storage cloud", False, str),
        "storageEndpoint": ("The storage endpoint point string for the"
                            " separate storage cloud", False, str),
        "storageAccount": ("The storage cloud account for the separate storage"
                           " cloud", False, str),
        "storageApiKey": ("The separate storage cloud API key",
                          False, str),
        "storageSecretKey": ("The separate storage cloud secret key",
                             False, str),
        "secondaryApiEndpoint": ("The endpoint contact string for the "
                                 "secondary backup cloud.", False, str),
        "secondaryApiAccount": ("The secondary cloud API account",
                                False, str),
        "secondaryStorageDelegate": ("If the secondary backup cloud has a "
                                     "separate storage provider its ID is "
                                     "specified here.", False, str),
        "secondaryStorageEndpoint": ("The endpoint contact string for the "
                                     "secondary separate storage cloud.",
                                     False, str),
        "secondaryStorageAccount": ("The account for the secondary storage "
                                    "separate cloud.",
                                    False, str),
        "secondaryStorageApiKey": ("The API key for the secondary storage "
                                   "separate cloud.",
                                   False, str),
        "secondaryStorageSecretKey": ("The API secret key for the secondary "
                                      "storage cloud.",
                                      False, str),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(BackupDataSource, self).__init__(
            conf, job_id, items_map, name, arguments)

    def get_safe_name(self, name):
        s = ""
        for c in name.lower():
            if c >= 'a' and c <= 'z':
                s = s + c
            elif c >= '0' and c <= '9':
                s = s + c
        return s

    def run(self):
        service_dir = self.conf.get_service_directory(self.args.serviceId)

        config_file_path = os.path.join(
            service_dir, "cfg", "enstratiusinitd.cfg")
        if not utils.safe_delete(config_file_path):
            msg = "Could not overwrite existing enstratiusinitd.cfg file."
            _g_logger.warn(msg)
            raise exceptions.AgentJobException(msg)

        with open(config_file_path, "w") as fptr:
            fptr.write(self.args.configuration.decode("utf-8"))

        tm_str = utils.get_time_backup_string()
        backup_file = "%s-%s-%s.zip" % \
                      (self.args.serviceId,
                       self.get_safe_name(self.args.dataSourceName),
                       tm_str)

        backup_path = os.path.join(self.conf.storage_temppath,
                                   backup_file + ".zip")

        script_name = self.items_map["script_name"]
        command = [self.conf.get_script_location(script_name),
                   self.args.serviceId,
                   self.args.dataSourceName,
                   config_file_path,
                   backup_path]

        cwd = self.conf.get_service_directory(self.args.serviceId)
        (stdout, stderr, rc) = utils.run_command(self.conf, command, cwd=cwd)
        if rc != 0:
            msg = "Unable to backup data source to " + backup_path + ": " + \
                  rc + " | " + stderr
            _g_logger.warn(msg)
            raise exceptions.AgentJobException(msg)

        _g_logger.info("Uploading backup %s to primary storage cloud." %
                       backup_path)

        primary_cloud_id = int(self.args.primaryCloudId)
        primary_api_key = self.args.primaryApiKey
        primary_secret_key = self.args.primarySecretKey
        primary_endpoint = self.args.apiEndpoint
        primary_account = self.args.apiAccount
        primary_region = self.args.primaryRegionId
        if primary_region is None:
            primary_region = self.conf.region_id

        if self.args.storageDelegate:
            primary_cloud_id = int(self.args.storageDelegate)
            primary_api_key = self.args.storageApiKey
            primary_secret_key = self.args.storageSecretKey
            primary_endpoint = self.args.storageEndpoint
            primary_account = self.args.storageAccount

        storagecloud.upload(
            primary_cloud_id,
            backup_path,
            self.args.toBackupDirectory,
            backup_file,
            primary_api_key,
            primary_secret_key,
            region_id=primary_region,
            endpoint=primary_endpoint,
            account=primary_account)

        secondary_cloud_id = self.args.secondaryCloudId
        secondary_api_key = self.args.secondaryApiKey
        secondary_secret_key = self.args.secondarySecretKey
        secondary_endpoint = self.args.secondaryEndpoint
        secondary_account = self.args.secondaryAccount
        secondary_region = self.args.secondaryRegionId

        if self.args.secondaryStorageDelegate:
            secondary_cloud_id = self.args.secondaryStorageDelegate
            secondary_endpoint = self.args.secondaryStorageEndpoint
            secondary_account = self.args.secondaryStorageAccount
            secondary_api_key = self.args.secondaryStorageApiKey
            secondary_secret_key = self.args.secondaryStorageSecretKey

        if secondary_cloud_id:
            storagecloud.upload(
                int(secondary_cloud_id),
                backup_path,
                self.args.toBackupDirectory,
                backup_file,
                secondary_api_key,
                secondary_secret_key,
                region_id=secondary_region,
                endpoint=secondary_endpoint,
                account=secondary_account)


def load_plugin(conf, job_id, items_map, name, arguments):
    return BackupDataSource(conf, job_id, items_map, name, arguments)
