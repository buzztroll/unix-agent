=================
dcm-agent testing
=================

## Setup Instructions for PyCharm on Mac 0SX

This assumes you have [PyCharm Professional Edition](http://www.jetbrains.com/pycharm/buy/) installed
and you have cloned [the es-ex-pyagent repo](https://www.github.com/enStratus/es-ex-pyagent)

1. Go into the project tests directory
  * ``` cd <whereeveryoucloned>/es-ex-pyagent/tests ```

2. Copy pycharm-debug.egg into this directory and set up creds file
  * ``` cp /Applications/PyCharm.app/pycharm-debug.egg .  ```
  * ``` touch creds ```
  * ``` echo "1 <aws_access_key> <aws_secret_key> us_west_oregon" > creds ```
  * Substitute in the above appropriate creds...you can have multiple.
  * See es-ex-pyagent/src/dcm/agent/storagecloud.py for all current providers

3. Start and setup VM distribution you are testing
  * example ``` vagrant up default-ubuntu-1204 ``` 
  * Vagrantfile has more options for distros
  * your cloned project directory will be mapped as a top level directory in the VM
  * so do:
  *  ``` vagrant ssh ```
  *  ``` sudo -i ```
  *  ``` cd /<projectdirectory>/es-ex-pyagent/tests ```
  *  ``` source testenv.sh --help ``` 
     
  *   then you can see the available options for environment variables.

  * Note that to set DCM_AGENT_STORAGE_CREDS that the creds file has to exist 
    and have an entry

  * Activate virtualenv and install deps
  *  ``` source /opt/dcm-agent/embedded/agentve.101/bin/activate ```
  *  ``` pip install -r /<projectdirectory>/es-ex-pyagent/src/requirements.txt ```
  *  ``` pip install -r /<projectdirectory>/es-ex-pyagent/src/test-requirements.txt ```
  *  ``` python /<projectdirectory>/es-ex-pyagent/src/setup.py develop  ```
  *  ``` pip install -r /<projectdirectory>/es-ex-pyagent/extensions/docker/dcmdocker/requirements.txt ```
  *  ``` pip install -r /<projectdirectory>/es-ex-pyagent/extensions/docker/dcmdocker/test-requirements.txt ```
  *  ``` python /<projectdirectory>/es-ex-pyagent/extensions/docker/dcmdocker/setup.py develop  ```

  * Install unzip then cp and unzip pycharm-debug.egg into virtualenv site-packages
  *  ``` apt-get install unzip ```
  *  ``` cp /<projectdirectory>/es-ex-pyagent/tests/pycharm-debug.egg /opt/dcm-agent/embedded/agentve.101/lib/python2.7/site-packages/ ```
  *  ``` unzip  /opt/dcm-agent/embedded/agentve.101/lib/python2.7/site-packages/pycharm-debug.egg ```

4. Setup PyCharm:
  * Remote debug configuration with localhost and port 5678
  * Set up virtualenv on host machine and set PyCharm project interpreter to it
  * ``` virtualenv --no-site-packages <whereever>/AgentVE ```
  * ``` source <whereever>/AgentVE/bin/activate ```
  *  ``` pip install -r /<projectdirectory>/es-ex-pyagent/src/requirements.txt ```
  *  ``` pip install -r /<projectdirectory>/es-ex-pyagent/src/test-requirements.txt ```
  *  ``` python setup.py develop  ```

5. Now back in the shell of your vagrant machine you can run:
  * ``` cd /<projectdirectory>/es-ex-pyagent/tests/ ```
  * ``` source testenv.sh --help ```
  * source testenv.sh again with your options and host machine private ip address
  * ``` nosetests dcm.agent.tests ```
  * You should see it connect to your PyCharm debugger where you can do the usual set breakpoints and step through
  
