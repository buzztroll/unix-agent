This document explains how to build and server the agent documentation
in a local test environment.

Build Documentation
-------------------

Create a virtualenv and install the agent and sphynx into it:

$ virtualenv -p <path to python 3> --no-site-packages ~/VE
$ . ~/VE/bin/activate
$ pip install --upgrade pip
$ pip install sphinx
$ cd <path to agent clone>/src
$ pip install .
$ python setup.py install
$ cd ../docs
$ make html
$ cd _build/html
$ python3 -m http.server
