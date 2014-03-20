import os
import pkg_resources


g_version = pkg_resources.require("es-ex-pyagent")[0].version


def get_root_location():
    return os.path.abspath(os.path.dirname(__file__))