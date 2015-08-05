"""This module provides the base functionality needed to create plugins to the
DCM Linux agent.  In it are the base classes needed to implement a plugin and
the API calls that plugins can use when interacting with the agent.  Each
extension command must be in its own python module and must contain the
following:

 - A class that extends :py:class:`dcm.agent.plugins.api.base.Plugin`
 - A module function named load_plugin with the following signature.

   .. code-block:: python

     load_plugin(conf, job_id, items_map, name, arguments)


This function must return an instance of the class defined in the first step.

The run method of the plugin class must return an instance of
:py:class:`dcm.agent.plugins.api.base.PluginReply`

If an exception occurs while processing the plugin should only throw exceptions
defined in the :py:mod:`dcm.agent.plugins.api.exceptions` module.

For an example of this see :py:mod:`dcm.agent.plugins.builtin.heartbeat`.
"""