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
import argparse
import importlib
import os
import types

import dcm.agent.plugins.builtin as builtins

filelist = [f for f in os.listdir(os.path.dirname(builtins.__file__))
            if not f.startswith("__")
            and not f.endswith(".pyc")]


def dynamic_import(f):
    """
    :param f: this is the filename
    :return:  reference to the imported module
    """
    filename = f[:-3]
    fpath = "dcm.agent.plugins.builtin." + filename
    x = importlib.import_module(fpath)

    return x


def get_protocol_argument_dict(x):
    """
    :param x: reference to imported module
    :return: protocol_arguments dict which is an
             attribute of the class in the module
    """
    for thing in dir(x):
        o = getattr(x, thing)
        z = getattr(o, 'protocol_arguments', None)
        if z is not None:
            return z


def output_markdown(f, pa_dict):
    """
    :param f: this is the filename
    :param pa_dict: this is the protocol_arguments dict
    :return:  the function prints to stdout the
              protocol_arguments dict in markdown format
    """
    flatstring = '## ' + f + ' parameters:\n'

    for key in sorted(list(pa_dict.keys())):
        value = pa_dict[key]
        flatstring += '- ' + key + ': ' + value[0] + '\n'
        flatstring += '    - optional: ' + '%s' % value[1] + '\n'
        flatstring += '    - type: ' + '%s' % get_type_string(value[2]) + '\n'
        flatstring += '    - default: ' + '%s' % str(value[3]) + '\n'
        flatstring += ''

    print(flatstring)
    return flatstring


def get_type_string(x):
    """
    :param x: this is object of type in
              the protocol_arguments dict
              in the builtins
    :return:  if type is FunctionType then
              we'll return a descriptive docstring __doc__
              otherwise just return __name__
    """
    if isinstance(x, types.FunctionType):
        return x.__doc__
    else:
        return x.__name__


def main():
    """
    :return: handler for the module
    """
    parser = argparse.ArgumentParser(
        prog='dcm-agent-gen-docs',
        description='A utility to output the agent protocol arguments in '
                    'an easy to read format.',
        usage='dcm-agent-gen-docs [> output file]')
    parser.parse_args()

    for f in filelist:
        x = dynamic_import(f)
        pa_dict = get_protocol_argument_dict(x)
        output_markdown(f, pa_dict)


if __name__ == "__main__":

    main()