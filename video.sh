#!/bin/bash

# 参数1,流媒体ip
# 参数2,流媒体port
# 参数3,流媒体宽度
# 参数4,流媒体高度
if [ $# -ne 4 ]; then
  echo "Usage: ./video.sh ip port w h"
  echo "--------"
  exit 1
else
  echo "ip = $1"
  echo "port = $2"
  echo "w = $3"
  echo "h = $4"
  echo "--------"
fi

/root/ffmpeg-dmo-2.1.3/ffmpeg -s $3x$4 -f video4linux2 -i /dev/video0 -f mpeg1video -b:v 100k -r 30 http://$1:$2/123456/$3/$4/

exit 0
