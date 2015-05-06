import os


def is_privatekey(keyfile):
    with open(keyfile, 'r') as f:
        if f.readline() == '-----BEGIN RSA PRIVATE KEY-----\n':
            return True
    return False


def main():
    for (dirpath, dirname, filename) in os.walk('/home'):
        if dirpath.endswith('.ssh'):
            for file in filename:
                filepath = os.path.join(dirpath, file)
                if is_privatekey(filepath):
                    cmd = 'rm %s' % filepath
                    os.system(cmd)

if __name__ == "__main__":
    main()
