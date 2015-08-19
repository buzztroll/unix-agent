DCM Agent Commands
==================

The dcm-agent's main purpose is to provide a remote set of commands to DCM.
The dcm-agent forms a websocket connection with DCM and advertises the set
of commands which DCM can invoke.  There is a set of built in
commands that can be found in the module dcm.agent.plugins.builtin.


Extension Plugins
-----------------

Via a well defined interface to the *command plugins* this set can be expanded
to support user defined functions.  When implementing a plugin a set of
utilities are defined for use by the author in the dcm.agent.plugin.api module.

Extension plugins are made by creating a python package that has one or more
modules in it which are properly constructed plugins.  The module is then
installed into the same python environment as the agent.  At that point the
tool `dcm-agent-add-plugins` can be used to locate all of the new plugins in
the newly installed package and add them to the existing DCM Agent
installation.

.. code-block:: bash

   $ dcm-agent-add-plugins <package name>

This program will search every submodule of the given package name for
dcm-agent plugins.  It will then modify the file /dcm/etc/plugins.conf to
make these plugins available to the agent.

Plugin Modules
--------------

Each plugin must be in its own python module that is conventionally named
after the command_name.  For example, the add_user command is implemented
in file called add_user.py.

DCM Agent Plugin API
---------------------

.. automodule:: dcm.agent.plugins.api
    :members:
    :noindex:

Plugin Base Class
-----------------

.. autoclass:: dcm.agent.plugins.api.base.Plugin
    :members:
    :noindex:

Plugin Reply Class
------------------

.. autoclass:: dcm.agent.plugins.api.base.PluginReply
    :members:
    :noindex:

Plugin Exceptions
-----------------

.. automodule:: dcm.agent.plugins.api.exceptions
    :members:
    :noindex:

Plugin Utility Functions
-------------------------

A set of utility functions are provided to plugin authors which allow for
interaction with the dcm-agent.

Parameter Validators
^^^^^^^^^^^^^^^^^^^^

When defining a plugin's accepted parameters the author must define a type
function.  Parameters come over the wire from DCM as strings.  They are
converted to specific types by calling these conversion functions.  If the
string is invalid these functions can throw a TypeError.  Functions
like str, int, bool, and float which are built into python can be used for
primitive types.  Plugin authors can write there own as well.  Below are a
set provided to authors.

.. autofunction:: dcm.agent.plugins.api.utils.base64type_convertor
    :noindex:

.. autofunction:: dcm.agent.plugins.api.utils.base64type_binary_convertor
    :noindex:

.. autofunction:: dcm.agent.plugins.api.utils.json_param_type
    :noindex:

.. autofunction:: dcm.agent.plugins.api.utils.user_name
    :noindex:

Logging
^^^^^^^

Plugin authors can make use of the standard python logging module in the
following way.

.. code-block:: python

   import logging

   _g_logger = logging.getLogger(__name__)
   _g_logger.debug("A log message")


Additionally plugins are allowed to log messages back to DCM.  Care should be
taken when choosing what to log back to DCM because this results in network
traffic and additional load on both the dcm-agent and DCM.  To log a message
to the DCM console the following function is used

.. autofunction:: dcm.agent.plugins.api.utils.log_to_dcm_console_job_details
    :noindex:

Utilities
^^^^^^^^^

The following functions are available to plugin authors.  Plugin authors should
not make any other calls into dcm.agent modules or class methods.

.. autofunction:: dcm.agent.plugins.api.utils.secure_delete
    :noindex:

.. autofunction:: dcm.agent.plugins.api.utils.run_command
    :noindex:

.. autofunction:: dcm.agent.plugins.api.utils.safe_delete
    :noindex:


An example dcm-agent plugin can be found `here
<https://github.com/enStratus/es-ex-pyagent/tree/master/extensions/example>`_.

