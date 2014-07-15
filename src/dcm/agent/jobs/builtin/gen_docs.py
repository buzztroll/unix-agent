
import os, importlib
import dcm.agent.jobs.builtin as jobs

## get files
filelist = [f for f in os.listdir(os.path.dirname(jobs.__file__)) 
            if not f.startswith("__init") 
            and not f.endswith("py") 
            and not f.startswith("gen_doc")
            ]


for f in filelist:
    filename = f[:-4]
    fpath = "dcm.agent.jobs.builtin." + filename
    x = importlib.import_module(fpath)
    for thing in dir(x):
        o = getattr(x, thing)
        z = getattr(o, 'protocol_arguments', None)
        if z is not None:
            print '## ' + filename + ' parameters'
            for key, value in z.iteritems():
                print '* ' + key + ': ' + value[0]
                print '    * optional: ' + '%s' % value[1] 
                print '    * type: ' + '%s' % value[2] 
                print ''
