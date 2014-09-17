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

import dcm.agent.jobs as jobs


class DockerListContainer(jobs.Plugin):

    protocol_arguments = {
        "quiet": ("", False, bool, None),
        "all": ("", False, bool, None),
        "trunc": ("", False, bool, None),
        "latest": ("", False, bool, None),
        "since": ("", False, str, None),
        "before": ("", False, str, None),
        "limit": ("", False, int, None),
        "size": ("", False, int, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(DockerListContainer, self).__init__(
            conf, job_id, items_map, name, arguments)



    def run(self):
        self.con.containers(quiet=self.args.quiet,
                            all=self.args.all,
                            trunc=self.args.trunc,
                            latest=self.args.latest,
                            since=self.args.since,
                            before=self.args.before,
                            limit=self.args.limit)


def load_plugin(conf, job_id, items_map, name, arguments):
    return DockerListContainer(conf, job_id, items_map, name, arguments)
