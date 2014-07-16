import os
import importlib
import dcm.agent.jobs.builtin as jobs

filelist = [f for f in os.listdir(os.path.dirname(jobs.__file__))
            if not f.startswith("__init")
            and not f.endswith("py")
]

def dynamic_import(f):
    filename = f[:-4]
    fpath = "dcm.agent.jobs.builtin." + filename
    x = importlib.import_module(fpath)
    return (filename,x)


def get_protocol_argument_dict(x):

    for thing in dir(x[1]):
        o = getattr(x[1], thing)
        z = getattr(o, 'protocol_arguments', None)

        if z is not None:
            print '## ' + x[0] + ' parameters'

            for key, value in z.iteritems():
                print '- ' + key + ': ' + value[0]
                print '    - optional: ' + '%s' % value[1]
                print '    - type: ' + '%s' % value[2]
                print ''


def main():
    for f in filelist:
        x = dynamic_import(f)
        get_protocol_argument_dict(x)

if __name__ == main():
    main()