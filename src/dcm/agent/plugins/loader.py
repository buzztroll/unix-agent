import configparser
import importlib
import logging
import os
import re

import dcm.agent.exceptions as exceptions
from dcm.agent.plugins.api.exceptions import AgentPluginConfigException


_g_logger = logging.getLogger(__name__)
_g_module_map = {}


def import_module(module_name):
    if module_name not in _g_module_map:
        module = importlib.import_module(module_name)
        _g_module_map[module_name] = module
    return _g_module_map[module_name]



# we could use stevedore for this if we are ok with another dependency
def load_python_module(
        module_name, conf, request_id, items_map, name, arguments):
    try:
        module = import_module(module_name)
        _g_logger.debug("Module acquired " + str(dir(module)))
        rc = module.load_plugin(conf, request_id, items_map, name, arguments)
        return rc
    except ImportError as iee:
        raise AgentPluginConfigException(
            "The module named %s could not be imported." % module_name, iee)
    except AttributeError as ae:
        _g_logger.exception("Could not load " + module_name)
        raise AgentPluginConfigException(
            "The module named %s does not have the load function."
            % module_name, ae)
    except:
        _g_logger.exception("An exception occurred loading the module")
        raise


def _load_python(conf, request_id, items_map, name, arguments):
    if 'module_name' not in items_map:
        raise AgentPluginConfigException(
            "The configuration for the %s plugin does not contain a "
            "module_name entry." % name)
    module_name = items_map['module_name']
    return load_python_module(
        module_name, conf, request_id, items_map, name, arguments)


_g_type_to_obj_map = {
    "python_module": _load_python
}


def register_plugin_loader(name, loader_func):
    _g_type_to_obj_map[name] = loader_func


def load_plugin(conf, items_map, request_id, name, arguments):
    _g_logger.debug("ENTER load_plugin")
    type_name = items_map["type"]
    if type_name not in _g_type_to_obj_map:
        raise AgentPluginConfigException(
            "The module type %s is not valid." % type_name)

    func = _g_type_to_obj_map[type_name]
    _g_logger.debug("calling load function")
    return func(conf, request_id, items_map, name, arguments)


def get_all_plugins(conf):
    conffile = conf.plugin_configfile
    if conffile is None or not os.path.exists(conffile):
        raise AgentPluginConfigException(
            "The plugin configuration file %s could not be found" % conffile)

    parser = configparser.SafeConfigParser()
    parser.read([conffile])
    section = parser.sections()

    all_plugins = {}
    for s in section:
        if s.startswith("plugin:"):
            try:
                items = parser.items(s)
                items_map = {}
                for i in items:
                    items_map[i[0]] = i[1]

                if "type" not in items_map:
                    _g_logger.warn("The section %s does not have an entry "
                                   "for type." % s)
                atype = items_map["type"]
                if atype not in _g_type_to_obj_map:
                    _g_logger.warn(
                        "The module type %s is not valid." % atype)
                all_plugins[s[7:]] = items_map
            except configparser.NoOptionError as conf_ex:
                raise AgentPluginConfigException(str(conf_ex))
    return all_plugins


def parse_plugin_doc(conf, name):
    _g_logger.debug("ENTER load_plugin")

    conffile = conf.plugin_configfile
    if conffile is None or not os.path.exists(conffile):
        raise AgentPluginConfigException(
            "The plugin configuration file %s could not be found" % conffile)

    parser = configparser.SafeConfigParser()
    parser.read([conffile])
    section = parser.sections()

    section_name = 'plugin:' + name
    for s in section:
        p = re.compile(s + "$")
        if p.match(section_name):
            _g_logger.debug(
                "load_plugin: found a match %s: %s" % (s, section_name))

            try:
                items = parser.items(s)
                items_map = {}
                for i in items:
                    items_map[i[0]] = i[1]

                if "type" not in items_map:
                    raise AgentPluginConfigException(
                        "The section %s does not have an entry for type."
                        % section_name)
                atype = items_map["type"]
                if atype not in _g_type_to_obj_map:
                    raise AgentPluginConfigException(
                        "The module type %s is not valid." % atype)

                return items_map
            except configparser.NoOptionError as conf_ex:
                raise AgentPluginConfigException(str(conf_ex))

    raise AgentPluginConfigException(
        "Plugin %s was not found." % name)


def get_module_features(conf, plugin_name, items_map):
    if items_map['type'] != 'python_module':
        return {}
    try:
        module = import_module(items_map['module_name'])
        get_features_func = getattr(module, 'get_features', None)
        if get_features_func is None:
            return {}
        return get_features_func(conf)
    except BaseException as ex:
        _g_logger.error("The agent is miss configured " + str(ex))
        raise
