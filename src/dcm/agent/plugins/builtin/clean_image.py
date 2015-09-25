#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import os
import sys
import threading

import dcm.agent.events.globals as events
import dcm.agent.logger as dcm_logger
from dcm.agent.messaging import persistence
import dcm.agent.utils as utils
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.builtin.remove_user as remove_user


_g_logger = logging.getLogger(__name__)


class CleanImage(plugin_base.Plugin):
    protocol_arguments = {
        "delUser":
            ("List of accounts to remove",
             False, list, None),
        "delHistory":
            ("Flag to delete all history files in all accounts",
             False, bool, None),
        "recovery":
            ("Create a recovery tar file of all the files that are deleted and encrypt it with the owners public key.",
             False, bool, None),
        "delKeys":
            ("Flag to delete private keys in users home directories",
             False, bool, False)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(CleanImage, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._done_event = threading.Event()
        self._topic_error = None
        self._db = persistence.SQLiteAgentDB(conf.storage_dbfile)

    def run_scrubber(self, opts):
        exe = os.path.join(os.path.dirname(sys.executable),
                           "dcm-agent-scrubber")
        cmd = [
            self.conf.system_sudo,
            '-E',
            exe
        ]
        if opts:
            cmd.extend(opts)

        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
        if rc != 0:
            return plugin_base.PluginReply(
                rc, message=stdout, error_message=stderr)
        return plugin_base.PluginReply(
            0, message="The image was scrubbed successfully")

    def _clean_topic_done(self, topic_error):
        self._topic_error = topic_error
        self._done_event.set()

    def run(self):
        try:
            events.global_pubsub.publish(
                events.DCMAgentTopics.CLEANUP,
                topic_kwargs={'request_id': self.job_id},
                done_cb=self._clean_topic_done)

            if self.args.delUser:
                dcm_logger.log_to_dcm_console_job_details(
                    job_name=self.name,
                    details='Deleting users.')
                for user in self.args.delUser:
                    rdoc = remove_user.RemoveUser(
                        self.conf,
                        self.job_id,
                        {'script_name': 'removeUser'},
                        'remove_user',
                        {'userId': user}).run()
                    if rdoc.get_return_code() != 0:
                        rdoc.set_message(rdoc.get_message() +
                                         " : Delete users failed on %s" % user)
                        return rdoc

            scrub_opts = ["-X", "-b", "-A"]
            if self.args.delHistory:
                scrub_opts.append("-H")
            if self.args.delKeys:
                dcm_logger.log_to_dcm_console_job_details(
                    job_name=self.name, details='Deleting private keys.')
                scrub_opts.append("-k")
            if self.args.recovery:
                # find the public key, if not there abort
                try:
                    username, public_key = self._db.get_owner()
                except:
                    _g_logger.exception("Could not get the owning user")
                    raise Exception(
                        "The agent could not encrypt the rescue image")
                if public_key is None:
                    raise Exception(
                        "The agent could not encrypt the rescue image")
                tar_file = "/tmp/dcm_agent_recovery.tar.gz"
                scrub_opts.extent(["-r", tar_file, "-e", public_key])

            self.run_scrubber(scrub_opts)

            self._done_event.wait()
            if self._topic_error is not None:
                return plugin_base.PluginReply(
                    1, error_message=str(self._topic_error))

            return plugin_base.PluginReply(
                0, message="Clean image command ran successfully")
        except Exception as ex:
            _g_logger.exception("clean_image failed: " + str(ex))
            return plugin_base.PluginReply(
                1, message=str(ex), error_message=str(ex))


def load_plugin(conf, job_id, items_map, name, arguments):
    return CleanImage(conf, job_id, items_map, name, arguments)
