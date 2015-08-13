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
