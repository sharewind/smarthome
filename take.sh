#!/bin/bash
# Modify KuaiZhan Project

# 参数1,图片title
# 参数2,图片name
if [ $# -ne 2 ]; then
  echo "Usage: ./take.sh title name"
  echo "--------"
  exit 1
else
  echo "title = $1"
  echo "name = $2"
  echo "--------"
fi

Stuffix="-树莓派@相册组"
Title="$1$Stuffix"
Name="/root/pi/take_photo/$2.jpg"

fswebcam -d /dev/video0 -r 640x320 --bottom-banner --title $Title --save $Name

exit 0
