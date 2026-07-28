#!/usr/bin/env bash
# Build and run the RAI container with a noVNC desktop.
#
#   ./run.linux.sh              build (if needed) + run detached
#   ./run.linux.sh --build      force rebuild
#   ./run.linux.sh --no-gpu     disable NVIDIA passthrough
#   ./run.linux.sh --shell      attach a shell after starting
#   ./run.linux.sh --logs       follow container logs
#   ./run.linux.sh --stop       stop and remove the container

set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-rai:humble}"
CONTAINER_NAME="${CONTAINER_NAME:-rai-desktop}"
ROS_DISTRO="${ROS_DISTRO:-humble}"
DEPENDENCIES="core_only"
NOVNC_PORT="${NOVNC_PORT:-6080}"
RDP_PORT="${RDP_PORT:-3389}"
SHM_SIZE="${SHM_SIZE:-2g}"
BIND_ADDR="${BIND_ADDR:-127.0.0.1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT_DIR="${SCRIPT_DIR}"
DOCKERFILE="${CONTEXT_DIR}/docker/Dockerfile"

FORCE_BUILD=0
USE_GPU=1
ATTACH_SHELL=0
FOLLOW_LOGS=0

for arg in "$@"; do
  case "$arg" in
    --build)      FORCE_BUILD=1 ;;
    --no-gpu)     USE_GPU=0 ;;
    --all-groups) DEPENDENCIES="all_groups" ;;
    --shell)      ATTACH_SHELL=1 ;;
    --logs)       FOLLOW_LOGS=1 ;;
    --stop)
      docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 \
        && echo "Removed ${CONTAINER_NAME}." || echo "Nothing to remove."
      exit 0
      ;;
    -h|--help)
      sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

command -v docker >/dev/null || { echo "docker not found in PATH." >&2; exit 1; }
[[ -f "${DOCKERFILE}" ]] || { echo "Dockerfile not found at ${DOCKERFILE}" >&2; exit 1; }

if [[ "${FORCE_BUILD}" -eq 1 ]] || ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
  echo ">> Building ${IMAGE_NAME} (ROS_DISTRO=${ROS_DISTRO}, DEPENDENCIES=${DEPENDENCIES})"
  DOCKER_BUILDKIT=1 docker build \
    --build-arg "ROS_DISTRO=${ROS_DISTRO}" \
    --build-arg "DEPENDENCIES=${DEPENDENCIES}" \
    -t "${IMAGE_NAME}" \
    -f "${DOCKERFILE}" \
    "${CONTEXT_DIR}"
else
  echo ">> Reusing existing image ${IMAGE_NAME} (use --build to rebuild)"
fi

GPU_ARGS=()
if [[ "${USE_GPU}" -eq 1 ]] && docker info 2>/dev/null | grep -qi nvidia; then
  GPU_ARGS=(--gpus all)
  echo ">> NVIDIA runtime detected, enabling --gpus all"
else
  echo ">> Running without GPU"
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

echo ">> Starting ${CONTAINER_NAME}"
docker run -d \
  --name "${CONTAINER_NAME}" \
  --shm-size "${SHM_SIZE}" \
  "${GPU_ARGS[@]}" \
  -p "${BIND_ADDR}:${NOVNC_PORT}:6080" \
  -p "${BIND_ADDR}:${RDP_PORT}:3389" \
  -e "ROS_DISTRO=${ROS_DISTRO}" \
  -e "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}" \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  "${IMAGE_NAME}" \
  sleep infinity

sleep 4
if [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null)" != "true" ]]; then
  echo ">> Container exited. Last logs:" >&2
  docker logs --tail 40 "${CONTAINER_NAME}" || true
  exit 1
fi

cat <<EOF

Container:  ${CONTAINER_NAME}
Browser:    http://localhost:${NOVNC_PORT}/vnc.html
RDP:        localhost:${RDP_PORT}

Shell:      docker exec -it ${CONTAINER_NAME} bash
Logs:       docker logs -f ${CONTAINER_NAME}
Stop:       ./run.linux.sh --stop
EOF

if [[ "${ATTACH_SHELL}" -eq 1 ]]; then
  exec docker exec -it "${CONTAINER_NAME}" bash
elif [[ "${FOLLOW_LOGS}" -eq 1 ]]; then
  exec docker logs -f "${CONTAINER_NAME}"
fi
