#!/usr/bin/env bash
# Run the RAI container with the noVNC desktop. Build it with ./build.linux.sh first.
set -euo pipefail

if docker container inspect rai-desktop >/dev/null 2>&1; then
  docker start rai-desktop >/dev/null
  exec docker exec -it rai-desktop bash
fi

docker run -it \
  --name rai-desktop \
  --gpus all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -e NVIDIA_VISIBLE_DEVICES=all \
  --device /dev/dxg \
  -v /usr/lib/wsl:/usr/lib/wsl:ro \
  -e LD_LIBRARY_PATH=/usr/lib/wsl/lib \
  -e DISPLAY=$DISPLAY \
  --shm-size 2g \
  -p 127.0.0.1:6080:6080 \
  -p 127.0.0.1:3390:3389 \
  -p 127.0.0.1:8501:8501 \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
  -e ROS_DISTRO=humble \
  -e MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
  -v "$HOME/projects/STM-Agentic-UAV/volume_data/rai_workspace:/rai/rai_workspace" \
  rai:humble
