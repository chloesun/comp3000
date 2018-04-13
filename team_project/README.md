# COMP 3000 Team Project
Create a filesystem for imgur with FUSE

## install libraries
```
sudo apt-get install libfuse-dev
sudo apt-get install python-dev
git clone https://github.com/libfuse/python-fuse.git
cd python-fuse
sudo python setup.py install
cd ..
./imgur_fs.py /home/users/Documents/imgur
```

(to mount the fs to this path, create the imgur folder first)
