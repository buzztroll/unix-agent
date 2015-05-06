import logging
import sys
from dcm.agent import jobs, utils
from dcm.agent.jobs.builtin.remove_user import RemoveUser


class CleanImage(jobs.Plugin):

    protocol_arguments = {
        "delUser":
        ("List of accounts to remove",
        False, list, None),
        "delKeys":
        ("Flag to delete private keys in users home directories",
        False, bool, False)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(CleanImage, self).__init__(
            conf, job_id, items_map, name, arguments)

    def delete_private_keys(self):
        res_doc =  {"return_code": 0,
                "message": "Keys were deleted successfully",
                "error_message": "",
                "reply_type": "void"}

        exe = self.conf.get_script_location("delete_keys.py")
        cmd = [
            '/usr/bin/sudo',
            sys.executable,
            exe
        ]

        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
        if rc != 0:
            res_doc["return_code"] = rc
            res_doc["message"] = stdout
            res_doc["error_message"] = stderr
        return res_doc

    def run(self, res_doc={}):
        if self.args.delUser:
            for user in self.args.delUser:
                rdoc = RemoveUser(self.conf,
                                  self.job_id,
                                  {'script_name': 'removeUser'},
                                  'remove_user',
                                  {'userId': user}).run()
                res_doc.update(rdoc)
                if res_doc["return_code"] != 0:
                    res_doc["message"] += " : Delete users failed on %s" % user
                    return res_doc

        if self.args.delKeys:
            res_doc = self.delete_private_keys()
            if res_doc['return_code'] != 0:
                return res_doc

        self.conf.state = "RUNNING"
        return {"return_code": 0,
                "message": "Clean image command ran successfully",
                "error_message": "",
                "reply_type": "void"}


def load_plugin(conf, job_id, items_map, name, arguments):
    return CleanImage(conf, job_id, items_map, name, arguments)