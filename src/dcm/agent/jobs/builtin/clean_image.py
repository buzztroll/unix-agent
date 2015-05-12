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
        False, bool, False),
        "sshConf":
        ("Flag to set ssh config with safe options",
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
            self.conf.system_sudo,
            '-E',
            sys.executable,
            exe
        ]

        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
        if rc != 0:
            res_doc["return_code"] = rc
            res_doc["message"] = stdout
            res_doc["error_message"] = stderr
        return res_doc

    def delete_history(self):
         res_doc = {"return_code": 0,
                    "message": "History deleted successfully",
                    "error_message": "",
                    "reply_type": "void"}

         exe = self.conf.get_script_location("delete_history.py")
         cmd = [
             self.conf.system_sudo,
             '-E',
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

        res_doc = self.delete_history()
        if res_doc['return_code'] != 0:
            return res_doc

        self.conf.state = "RUNNING"
        return {"return_code": 0,
                "message": "Clean image command ran successfully",
                "error_message": "",
                "reply_type": "void"}


def load_plugin(conf, job_id, items_map, name, arguments):
    return CleanImage(conf, job_id, items_map, name, arguments)