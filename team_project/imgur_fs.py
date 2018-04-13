#!/usr/bin/env python
from urlparse import urlparse
import requests
import os, stat, errno
# Based on example in python-fuse at https://github.com/libfuse/python-fuse
# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
# import Fuse class as Fuse from fuse library to avoid having to write fuse everywhere
from fuse import Fuse

# check fuse version
if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

# api version of python-fuse
fuse.fuse_python_api = (0, 2)

# imgur api crendentials
CLIENT_ID = 'cd89bf737db7404'
CLIENT_SECRET = 'a68d534095f8ec6f3e880a5baa71b00d2f14b03a'

# GET Gallery see https://apidocs.imgur.com/#eff60e84-5781-4c12-926a-208dc4c7cc94
RESPONSE = requests.get(
    'https://api.imgur.com/3/gallery/hot/rising/day/1?showViral=true&mature=false&album_previews=false',
    headers = {'Authorization': 'Client-ID ' + CLIENT_ID}
)

# stop if we have an error
assert RESPONSE.status_code == 200

# extract file's data from json response
FILES_METADATA = RESPONSE.json()['data']

# split the path and take last item from the path (the filename)
# ex: http://blah.com/blah/blah/image.jpg becomes image.jpg
def link_to_filename(link):
    return os.path.split(urlparse(link).path)[-1]

# add a file to a dictionary key is filename, value is dictionary containing size and bytes of the file
# and the link(url) to the file
def normalize_metadata_entry(acc, f):
    if 'size' in f and 'link' in f:
        acc[link_to_filename(f['link'])] = {'size': f['size'], 'link': f['link']}
    return acc

# Extract image file data (unnormalized) from FILES_METADATA dictionary (a complicated structure)
# filter out items that are not images and not ending in .png
def get_files():
    return [f['images'][0] for f in FILES_METADATA if 'images' in f and f['images'][0]['link'].endswith('.png')]

# Reduce into our dictionary all metadata into a structure that contains only what we need
# Complex structure turns into a dictionary with this form:
# {"<filename>": {"size": <number of bytes>, "link": "<url fo file>"}, ...}
FILES = reduce(normalize_metadata_entry, get_files(), {})

# default stats for fuse (constructor)
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

# implements the file system
class imgur_FS(Fuse):

    def getattr(self, path):
        st = imgur_Stat()
        if path == '/':
            # 755 =>
            #          RWX
            # binary   111 = 7 = rwx
            # binary   101 = 5 = r-x
            # binary   000 = 0 = ---
            #    5 is owner with read and execute
            #    5 is group with read and execute
            #    5 is other with read and execute
            st.st_mode = stat.S_IFDIR | 0o555
            st.st_nlink = 2
        elif FILES.has_key(os.path.split(path)[-1]):
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            # set the size of the file
            st.st_size = FILES[os.path.split(path)[-1]]['size']
        else:
            return -errno.ENOENT
        return st

    # get the filenames and convert to utf-8 (fuse.Direntry expects utf-8 encoded strings)
    # generate a stream of directory entries
    def readdir(self, path, offset):
        paths = ['.', '..'] + [fn.encode('utf-8') for fn in FILES.keys()]
        for r in paths:
            yield fuse.Direntry(r)

    # open files form FILES dictionary, return ENOENT if absent
    def open(self, path, flags):
        if os.path.split(path)[-1] not in FILES.keys():
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

    # read the requestesd part from imgur using HTTP
    # we don't read the entire file here. we only request size, number of bytes, starting at the specified offset
    # This is done by using the range header in HTTP  https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests
    def read(self, path, size, offset):
        resp = requests.get(
            FILES[os.path.split(path)[-1]]['link'],
            headers = {'Range': 'bytes=' + str(offset) + '-' + str(size + offset - 1)}
        )
        # 206: partial content because of range
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
