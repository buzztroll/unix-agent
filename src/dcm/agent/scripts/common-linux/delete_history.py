import os
import re


def main(bin_path):
    lookfor = '.*history'
    for (dirpath, dirname, filename) in os.walk('/home'):
        for file in filename:
            if re.match(lookfor, file):
                cmd = '%s %s' % \
                      (os.path.join(bin_path, 'secureDelete'),
                       os.path.join(dirpath, file))
                os.system(cmd)

if __name__ == "__main__":
    bin_path = os.path.dirname(os.path.abspath(__file__))
    main(bin_path)