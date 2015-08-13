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
import argparse
import configparser
import importlib
import pkgutil
import sys
import types

import dcm.agent.config as agent_config
import dcm.agent.plugins.api.base as plugin_base


def setup_command_line_parser():
    parser = argparse.ArgumentParser(
        description='DCM Agent Plugin Configuration Program.')

    parser.add_argument("--configfile", "-c",
                        dest="conffile",
                        help="A path to the agents configuration file",
                        default="/dcm/etc/agent.conf")
    parser.add_argument("--prefix", "-p",
                        dest="prefix",
                        help="A string to prepend to all the command names found",
                        default="")
    parser.add_argument('module_name', type=str, metavar="<module name>",
                        help="The name of the module where this program will search for plugins.")
    return parser


def get_plugin_details(full_module_name, short_module_name):
    mod = importlib.import_module(full_module_name)
    lp_func = getattr(mod, 'load_plugin', None)
    if lp_func is None and isinstance(types.FunctionType, lp_func):
        return False

    for d in mod.__dict__:
        c = getattr(mod, d)
        try:
            if issubclass(c, plugin_base.Plugin):
                cmd_name = getattr(c, 'command_name', None)
                if cmd_name is None:
                    cmd_name = short_module_name
                long_runner = getattr(c, 'long_runner', None)

                return (cmd_name, long_runner)
        except TypeError:
            pass
    return None


def find_plugins(base_module_name):
    plugin_list = []
    try:
        base_module = importlib.import_module(base_module_name)
        for loader, module_name, is_pkg in pkgutil.walk_packages(
                base_module.__path__):
            full_mod_name = base_module_name + '.' + module_name
            if is_pkg:
                fnd_list = find_plugins(full_mod_name)
                plugin_list.extend(fnd_list)
            else:
                plugin_info = get_plugin_details(full_mod_name, module_name)
                if plugin_info is not None:
                    plugin_list.append({'module_name': full_mod_name,
                                        'command_name': plugin_info[0],
                                        'long_runner': plugin_info[1]})
    except Exception as ex:
        print(str(ex))
    return plugin_list


def rewrite_conf(conf_file, module_list, prefix):
    parser = configparser.ConfigParser()
    parser.read(conf_file)
    for m in module_list:
        section_name = "plugin:%s%s" % (prefix, m['command_name'])
        try:
            parser.add_section(section_name)
        except configparser.DuplicateSectionError:
            raise Exception("The plugin %s already exists.  Please rename it."
                            % m['command_name'])
        parser.set(section_name, "type", "python_module")
        parser.set(section_name, "module_name", m['module_name'])
        if m['long_runner'] is not None:
            parser.set(section_name, "long_runner", str(m['long_runner']))

    with open(conf_file, "w") as fptr:
        parser.write(fptr)


def main(args=sys.argv):
    parser = setup_command_line_parser()
    opts = parser.parse_args(args=args[1:])

    conf = agent_config.AgentConfig([opts.conffile])

    module_list = find_plugins(opts.module_name)
    rewrite_conf(conf.plugin_configfile, module_list, opts.prefix)

    print("Updated the plugin configuration file %s" % conf.plugin_configfile)
    for m in module_list:
        print("\tAdded command %s" % m['command_name'])
    print("Restart the agent for changes to take effect.")


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
