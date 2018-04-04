#!/usr/bin/env python
from urlparse import urlparse
import requests
import os, stat, errno
# Base on example in python-fuse at https://github.com/libfuse/python-fuse
# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse


if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

CLIENT_ID = 'cd89bf737db7404'
CLIENT_SECRET = 'a68d534095f8ec6f3e880a5baa71b00d2f14b03a'
RESPONSE = requests.get('https://api.imgur.com/3/gallery/hot/rising/day/1?showViral=true&mature=false&album_previews=false', headers={'Authorization': 'Client-ID ' + CLIENT_ID})
assert RESPONSE.status_code == 200
FILES_METADATA = RESPONSE.json()['data']

def link_to_filename(link):
    return os.path.split(urlparse(link).path)[-1]
def normalize_metadata_entry(acc, f):
    #print '=' * 1000, json.dumps(f)
    if 'size' in f and 'link' in f:
        #print '+' * 1000, 'Doing good things...'
        acc[link_to_filename(f['link'])] = {'size': f['size'], 'link': f['link']}
    return acc

def get_files():
    return [f['images'][0] for f in FILES_METADATA if 'images' in f and f['images'][0]['link'].endswith('.png')]

FILES = reduce(normalize_metadata_entry, get_files(), {})

print '$' * 10000, repr(FILES.keys())

hello_path = '/hello'
hello_str = 'Hello World!\n'

class imgur_Stat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

class imgur_FS(Fuse):

    def getattr(self, path):
        st = imgur_Stat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        elif FILES.has_key(os.path.split(path)[-1]):
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            st.st_size = FILES[os.path.split(path)[-1]]['size']
        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        paths = ['.', '..'] + [fn.encode('ascii') for fn in FILES.keys()]
        for r in paths:
            yield fuse.Direntry(r)

    def open(self, path, flags):
        if os.path.split(path)[-1] not in FILES.keys():
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

    def read(self, path, size, offset):
        resp = requests.get(
            FILES[os.path.split(path)[-1]]['link'],
            headers = {'Range': 'bytes=' + str(offset) + '-' + str(size + offset - 1)}
        )
        if resp.status_code != 200 and resp.status_code != 206:
            return -errno.ENOENT
        data = resp.content
        return data




def main():

    usage="""
Userspace imgur_fs.py example

""" + Fuse.fusage
    server = imgur_FS(version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    main()