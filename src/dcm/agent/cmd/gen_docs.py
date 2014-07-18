import os
import importlib
import dcm.agent.jobs.builtin as jobs

filelist = [f for f in os.listdir(os.path.dirname(jobs.__file__))
            if not f.startswith("__init")
            and not f.endswith(".pyc")
]


def dynamic_import(f):
    """
    :param f: this is the filename
    :return:  reference to the imported module
    """
    filename = f[:-3]
    fpath = "dcm.agent.jobs.builtin." + filename
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
    for key, value in pa_dict.iteritems():
        flatstring += '- ' + key + ': ' + value[0] + '\n'
        flatstring += '    - optional: ' + '%s' % value[1] + '\n'
        flatstring += '    - type: ' + '%s' % value[2] + '\n'
        flatstring += ''

    return flatstring


def main():
    """
    :return: handler for the module
    """
    for f in filelist:
        x = dynamic_import(f)
        pa_dict = get_protocol_argument_dict(x)
        output_markdown(f, pa_dict)


if __name__ == main():
    main()
