import os
import importlib
import dcm.agent.jobs.builtin as jobs

filelist = [f for f in os.listdir(os.path.dirname(jobs.__file__))
            if not f.startswith("__init")
            and not f.endswith("py")
]

def dynamic_import(f):
    """
    :param f: this is the filename
    :return:  reference to the imported module
    """
    filename = f[:-4]
    fpath = "dcm.agent.jobs.builtin." + filename
    x = importlib.import_module(fpath)

    return x


def get_protocol_argument_dict(x):
    """
    :param x: reference to imported module
    :return: protocol_arguments dict which is an
             attribute of the class in the module
    """
    class_name = dir(x)[0]
    class_object = getattr(x, class_name, None)
    protocol_argument_dict = class_object.protocol_arguments

    return protocol_argument_dict

def output_markdown(f,pa_dict):
    """
    :param f: this is the filename
    :return:  the function prints to stdout the
              protocol_arguments dict in markdown format
    """
    print '## ' + f + ' parameters'
    for key, value in pa_dict.iteritems():
        print '- ' + key + ': ' + value[0]
        print '    - optional: ' + '%s' % value[1]
        print '    - type: ' + '%s' % value[2]
        print ''

def main():
    """
    :return: handler for the module
    """
    for f in filelist:
        x = dynamic_import(f)
        pa_dict = get_protocol_argument_dict(x)
        output_markdown(f,pa_dict)

if __name__ == main():
    main()