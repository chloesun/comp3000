# comp3000
create a filesystem for imgur with FUSE

sudo apt-get install libfuse-dev
sudo apt-get install python-dev
sudo python setup.py install
./imgur_fs.py /home/users/Documents/imgur
(to mount the fs to this path, create the imgur folder first)
