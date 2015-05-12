import os, sys


def is_privatekey(keyfile):
    with open(keyfile, 'r') as f:
        if f.readline() == '-----BEGIN RSA PRIVATE KEY-----\n':
            return True
    return False


def main(bin_path):
    for (dirpath, dirname, filename) in os.walk('/home'):
        if dirpath.endswith('.ssh'):
            for file in filename:
                filepath = os.path.join(dirpath, file)
                if is_privatekey(filepath):
                    cmd = '%s %s' % \
                        (os.path.join(bin_path, 'secureDelete'),
                         filepath)
                    os.system(cmd)

if __name__ == "__main__":
    bin_path = os.path.dirname(os.path.abspath(__file__))
    main(bin_path)
