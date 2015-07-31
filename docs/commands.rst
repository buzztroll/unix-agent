DCM Agent Commands
==================

The dcm-agent's main purpose is to provide a remote set of commands to DCM.
The dcm-agent forms a websocket connection with DCM and advertises the set
of commands which DCM can invoke on the server.  There is a set of built in
commands that can be found in the module dcm.agent.plugins.builtin.


Extension Plugins
-----------------

Via a well defined interface to the `command plugins` this set can be expanded
to support user defined function.  When implementing a set of utilities are
defined for use by the author in the
`dcm.agent.plugin.api module <dcm.agent.plugins.api.html>`_.

Extension plugins are made by creating a python package that has one or more
modules in it which are properly constructed plugins.  The modules is then
installed into the same python environment as the agent.  At that point the
tool `dcm-agent-add-plugins` can be used to locate all of the new plugins in
the newly installed module and add them to the existing DCM Agent installation.

.. code-block:: bash

   $ dcm-agent-add-plugins <module name>

This program will search every submodule of the given module name for dcm-agent
plugins.  It will then modify the file /dcm/etc/plugins.conf to make these
plugins available to the agent.

Plugin Modules
--------------

Each plugin must be in its own python module that is conventionally named
after the command_name.  For example, the add_user command is implemented
in file called add_user.py.

More details on how to implement a plugin can be found
`here <dcm.agent.plugins.api.html>`_.

An example dcm-agent plugin can be found `here
<https://github.com/enStratus/es-ex-pyagent/tree/master/extensions/example>`_.


