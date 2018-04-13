#!/usr/bin/env python2
from urlparse import urlparse
from subprocess import call
import requests

import sys, os, stat, errno
# Base on example in python-fuse at https://github.com/libfuse/python-fuse
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

#prints the introduction when the program is called
def introduction():
    print("WELCOME TO IMGUR AS A FILE SYSTEM")
    print("=================================")
    print('Your file system is mounted at: ', sys.argv[1])
    print("The input method goes as follows:")
    print("	You will be prompted for filters to search through imgur.")
    print("	The prompts will tell you specifically what the proper inputs are. The program will not work if given incorrect input.")
    print("	The photos that have been requested will appear in your mounted folder.")
    print("	To view a new set of photos, run the program again.")
    print("	Thanks :)\n")

#searches galleries through user entered filters
#Key		Required	Value
#section	optional	hot | top | user. Defaults to hot
#sort		optional	viral | top | time | rising (only available with user section). Defaults to viral
#page		optional	integer - the data paging number
#window		optional	Change the date range of the request if the section is top. Accepted values are day | week | month | year | all. Defaults to day
def gallery_search():
    global newpath
    section = raw_input("Section (hot, top, user): ")
    sort = raw_input("Sort Method (viral, top, time, rising): ")
    window = raw_input("Timeframe (day, week, month, year, all): ")
    page = raw_input("Page Number: ")
    s = 'https://api.imgur.com/3/gallery/'
    s += section
    s += '/'
    s += sort
    s += '/'
    s += window
    s += '/'
    s += page
    s += '?showViral=true&mature=false&album_previews=false'
    return s

#searches subreddits through user entered filters
#Key		Required	Value
#subreddit	required	pics - A valid subreddit name
#sort		optional	time | top - defaults to time
#page		optional	integer - the data paging number
#window		optional	Change the date range of the request if the sort is "top". Options are day | week | month | year | all. Defaults to week
def subreddit_search():
    global newpath
    subreddit = raw_input("Subreddit Name: ")
    sort = raw_input("Sort Method (top, time): ")
    window = raw_input("Timeframe ONLY APPLIES IF SORT WAS TOP (day, week, month, year, all): ")
    page = raw_input("Page Number: ")
    s = 'https://api.imgur.com/3/gallery/r/'
    s += subreddit
    s += '/'
    s += sort
    s += '/'
    s += window
    s += '/'
    s += page
    return s

#uses the link as the filename
def link_to_filename(link):
    return os.path.split(urlparse(link).path)[-1]

#uses the data (f) to create a structure (acc) just consisting of the size and link for each file
#this only applies to gallery search

def normalize_metadata_entry(acc, f):
    if 'size' in f and 'link' in f:
        acc[link_to_filename(f['link'])] = {'size': f['size'], 'link': f['link']}
    return acc

#uses the data (f) to create a structure (acc) just consisting of the size and link for each file
#this only applies to subreddit search
def normalize_metadata_entry_subreddit(acc, f):
    #print '=' * 1000, json.dumps(f)
    if 'link' in f:
        acc[link_to_filename(f['link'])] = {'size': f['size'], 'link': f['link']}
    return acc

#get the image files from the FILES_METADATA
#this only applies to gallery search
def get_files():
    return [f['images'][0] for f in FILES_METADATA if 'images' in f and (f['images'][0]['link'].endswith('.png') or f['images'][0]['link'].endswith('.jpg'))]

#the introduction to the imgur fuse program
introduction()

#loop until valid user input and response from server
while True:
    try:
        search = input("For gallery search, input '1'. For Subreddit search, input '2': ")

        REQUESTSTRING = ""
		
		#search value of 1 is for a gallery search
        if search == 1:
            REQUESTSTRING = gallery_search()
		#if not searching for a glallery, search for subreddit
        else:
            REQUESTSTRING = subreddit_search()

		#the client ID for the search
        CLIENT_ID = 'cd89bf737db7404'
        CLIENT_SECRET = 'a68d534095f8ec6f3e880a5baa71b00d2f14b03a'
        print(REQUESTSTRING)
		#Retrieves the response from the search request
        RESPONSE = requests.get(REQUESTSTRING, headers={'Authorization': 'Client-ID ' + CLIENT_ID})
        print(RESPONSE.status_code)
		#checks if the status code is equal to 200
        assert RESPONSE.status_code == 200
		#stores the data in FILES_METADATA
        FILES_METADATA = RESPONSE.json()['data']

		#Data can be retrieved in slightly different ways. This accounts for it
        FILES = reduce(normalize_metadata_entry, get_files(), {})
        if not FILES:
            FILES = reduce(normalize_metadata_entry_subreddit, FILES_METADATA, {})

        break
    except:
        print("There was a problem with the requested search")

#if the requested mount folder is already mounted, unmounts it
call(["sudo","umount",sys.argv[1]])

#From https://github.com/libfuse/python-fuse adapted for imgur

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

