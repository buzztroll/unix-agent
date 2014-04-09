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
import datetime
from dcm.agent import exceptions
import dcm.agent.utils as utils
import dcm.agent.jobs.direct_pass as direct_pass
from dcm.agent import storagecloud


_g_logger = logging.getLogger(__name__)


class BackupDataSource(direct_pass.DirectPass):

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(BackupDataSource, self).__init__(
            conf, job_id, items_map, name, arguments)

        try:
            self._service_id = arguments["serviceId"]
            self._config_data = arguments["configuration"]
            self._data_source_name = arguments["dataSourceName"]
            self._cloud_id = arguments["inCloudId"]
            self._config_data = arguments["configuration"]
            self._access_key = arguments["cloudAccessKey"]
            self._secret_key = arguments["cloudSecretKey"]
            self._container_name = arguments["toBackupDirectory"]
            self._delegate = self.arguments.get("deletegate", None)
            self._endpoint = self.arguments.get("endpoint", None)
            self._account = self.arguments.get("account", None)
            self._region_id = self.arguments.get("providerRegionId",
                                                 conf.region_id)
        except KeyError as ke:
            raise exceptions.AgentPluginConfigException(
                "The plugin %s requires the option %s" % (name, ke.message))

    def get_safe_name(self, name):
        s = ""
        for c in name.lower():
            if c >= 'a' and c <= 'z':
                s = s + c
            elif c >= '0' and c <= '9':
                s = s + c
        return s

    def run(self):
        service_dir = self.conf.get_service_directory(self._service_id)

        config_file_path = os.path.join(
            service_dir, "cfg", "enstratiusinitd.cfg")
        if not utils.safe_delete(config_file_path):
            msg = "Could not overwrite existing enstratiusinitd.cfg file."
            _g_logger.warn(msg)
            raise exceptions.AgentJobException(msg)

        with open(config_file_path, "w") as fptr:
            fptr.write(self._config_data)

        nw = datetime.datetime.now()
        tm_str = nw.strftime("%Y%m%d.%H%M%S.%f")
        backup_file = "%s-%s-%s.zip" % \
                      (self._service_id,
                       self.get_safe_name(self._data_source_name),
                       tm_str)

        backup_path = os.path.join(self.conf.storage_temppath,
                                   backup_file + ".zip")

        script_name = self.items_map["script_name"]
        command = [self.conf.get_script_location(script_name),
                   self._service_id,
                   self._data_source_name,
                   config_file_path,
                   backup_path]

        cwd = self.conf.get_service_directory(self._service_id)
        (stdout, stderr, rc) = utils.run_command(self.conf, command, cwd=cwd)
        if rc != 0:
            msg = "Unable to backup data source to " + backup_path + ": " + \
                  rc + " | " + stderr
            _g_logger.warn(msg)
            raise exceptions.AgentJobException(msg)

        _g_logger.info("Uploading backup %s to primary storage cloud." %
                       backup_path)

        storagecloud.upload(
            self._cloud_id,
            backup_path,
            self._container_name,
            backup_file,
            self._access_key,
            self._secret_key,
            region_id=self._region_id,
            delegate=self._delegate,
            endpoint=self._endpoint,
            account=self._account)

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(conf, job_id, items_map, name, arguments):
    return BackupDataSource(conf, job_id, items_map, name, arguments)
