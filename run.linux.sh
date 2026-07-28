#!/usr/bin/env bash
# Run the RAI container with the noVNC desktop. Build it with ./build.linux.sh first.
set -euo pipefail

if docker container inspect rai-desktop >/dev/null 2>&1; then
  docker start rai-desktop >/dev/null
  exec docker exec -it rai-desktop bash
fi

docker run -it \
  --name rai-desktop \
  --shm-size 2g \
  -p 127.0.0.1:6080:6080 \
  -p 127.0.0.1:3390:3389 \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
  -e ROS_DISTRO=humble \
  -v "$HOME/projects/rai/volume_data/rai_workspace:/rai/rai_workspace" \
  rai:humble
