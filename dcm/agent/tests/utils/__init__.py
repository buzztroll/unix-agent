import os


def get_conf_file():
    path = os.path.dirname(__file__)
    path = os.path.dirname(path)
    return os.path.join(path, "etc/agent.conf")
