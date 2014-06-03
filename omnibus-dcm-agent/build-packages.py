import os
import yaml

with open(".kitchen.yml", 'r') as f:
    config = yaml.load(f.read())

print config
for platform in config['platforms']:
    print "Building for %s" % platform['name']
    os.system("kitchen converge default-" % platform['name'])
