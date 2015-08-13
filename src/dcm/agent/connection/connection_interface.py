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
import dcm.agent.utils as agent_util


class ConnectionInterface(object):

    @agent_util.not_implemented_decorator
    def send(self, doc):
        """
        Write a json document down the connection
        """
        pass

    @agent_util.not_implemented_decorator
    def connect(self, receive_callback, handshake_manager):
        pass

    @agent_util.not_implemented_decorator
    def close(self):
        """
        Close the connection.  This gives implementations a chance to shutdown
        any associated threads
        """
        pass
