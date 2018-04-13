# COMP 3000 Team Project
Create a filesystem for imgur with FUSE

## install libraries
```
sudo apt-get install libfuse-dev
sudo apt-get install python-dev
sudo python setup.py install
./imgur_fs.py /home/users/Documents/imgur
```

(to mount the fs to this path, create the imgur folder first)
