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
#!/usr/bin/env python
import shutil
import os

from docker.client import Client
from docker.utils import kwargs_from_env


def get_client(version, **kwargs):
    return Client(version=version, **kwargs)


def create_container(client, image, detach, command):
    return client.create_container(image=image,
                                   detach=detach,
                                   command=command)


def copy_scripts():
    shutil.copy('../../bin/upgrade.py', '.')
    shutil.copy('../../bin/upgrade.sh', '.')


def build_image(client, image_name, path='.'):
    return [line for line in client.build(path=path, tag=image_name)]


def cleanup():
    os.remove('upgrade.sh')
    os.remove('upgrade.py')


def get_logs(client, container):
    return client.logs(container)


def main():
    copy_scripts()

    # kwargs_from_env is helper function for working with boot2docker
    # look at https://github.com/docker/docker-py/blob/master/docs/boot2docker.md for more info
    client = get_client(version='1.15', **kwargs_from_env())

    image_name = 'agent/upgrader'

    # build image and start container with it
    build_image(client, image_name)
    container = create_container(client, image_name, True, '/bin/bash /run_forever.sh')
    client.start(container)

    # install old(er) agent in container
    agent_url = os.getenv('AGENT_BASE_URL') or "http://linux.stable.agent.enstratius.com"
    agent_version = os.getenv('AGENT_VERSION') or "0.11.1"
    exec_id = client.exec_create(container, '/bin/bash /install_agent.sh %s %s' % (agent_url, agent_version))
    exec_response = client.exec_start(exec_id)
    print(exec_response)

    # assert that old agent version is correct
    current_version_id = client.exec_create(container, '/opt/dcm-agent/embedded/agentve/bin/dcm-agent --version')
    current_version_response = client.exec_start(current_version_id)
    print(current_version_response)
    assert agent_version in current_version_response

    # run upgrade script with specified version
    agent_upgrade_version = os.getenv('AGENT_UPGRADE_VERSION') or "0.11.2"
    agent_upgrade_url = os.getenv('AGENT_UPGRADE_BASE_URL') or "http://linux.stable.agent.enstratius.com"
    upgrade_id = client.exec_create(container, '/bin/bash /upgrade.sh --version %s --package_url %s' % (agent_upgrade_version, agent_upgrade_url))
    upgrade_response = client.exec_start(upgrade_id)


    # assert that upgrade agent version is correct
    upgrade_version_id = client.exec_create(container, '/opt/dcm-agent/embedded/agentve/bin/dcm-agent --version')
    upgrade_version_response = client.exec_start(upgrade_version_id)
    print(upgrade_version_response)
    assert agent_upgrade_version in upgrade_version_response

    print(get_logs(client, container))
    client.stop(container)


if __name__ == "__main__":
    main()

