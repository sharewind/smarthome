#!/bin/bash
set -x
echo "================= install dependency ============= "
sudo apt-get install libavahi-compat-libdnssd1
sudo pip install virtualenv
sudo pip install supervisor

virtualenv env
. env/bin/activate 

#pip install -r requirements.txt 
pip install -r requirements.txt -i http://localhost:9999/simple

mkdir -pv /opt/logs/nginx/  
mkdir -pv /opt/logs/supervisord/  
mkdir -pv /opt/logs/smart_home/
