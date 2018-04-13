# COMP 3000 Team Project
Developed a virtual file system to mount the filtered images from imgur to a local mount point, so we can read and interact with them.

## Features
#### Gallery search based on the prompted options
#### Subreddit galleries search based on the prompted options

## Install
```
sudo apt-get install libfuse-dev
sudo apt-get install python-dev
git clone https://github.com/libfuse/python-fuse.git
cd python-fuse
sudo python setup.py install
cd ..
chmod +x imgur_fs.py
./imgur_fs.py /home/user/Documents/imgur
```

(to mount the fs to this path, create the imgur folder first)
