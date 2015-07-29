"""
DCM Agent Plugin API

This module provides the base functionality needed to create plugins to the
DCM linux agent.  In it are the base classes needed to implement a plugin and
the API calls that plugins can use when interacting with the agent.  Each
extension command must be in its own python and must contain the following:

1) A class that extends dcm.agent.plugins.api.base.PluginInterface.  Modules
should will dcm.agent.plugins.api.base.Plugin which is a subclass of
the former.

2) A module function name load_plugin with the following signature:
     load_plugin(conf, job_id, items_map, name, arguments)
This function must return an instance of the class defined in step 1.

The run method of the plugin class must return a dictionary with the following
elements:

 {
    "return_code": <0 for success, non-0 for failure>
    "reply_type": <a string which defines the reply_object layout>
    "reply_object": <a module defined reply payload>
    "message": <A string describing the action>
    "error_message": <A string describing any error that occurred>
}

If an exception occurs while processing the plugin should only throw exceptions
defined in the dcm.agent.plugins.api.exceptions module.

For an example of this see dcm.agent.plugins.builtin.heartbeat.

"""