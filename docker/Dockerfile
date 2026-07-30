# Copyright (C) 2024 Robotec.AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ARG ROS_DISTRO=humble
FROM osrf/ros:${ROS_DISTRO}-desktop-full

ARG DEPENDENCIES=core_only
ENV DEBIAN_FRONTEND=noninteractive

# Check whether the $DEPENDENCIES ARG has a valid value
RUN /bin/bash -c 'if [ "${DEPENDENCIES}" != "core_only" ] && [ "${DEPENDENCIES}" != "all_groups" ]; then \
  echo Error: invalid DEPENDENCIES value. Valid values "core_only", "all_groups" && exit 1; \
fi'

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

# Set up the environment to use Fast DDS
ENV FASTRTPS_DEFAULT_PROFILES_FILE=/rai/docker/fastrtps_config.xml
ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
RUN apt update && apt install -y --no-install-recommends \
    python3 \
    python3-pip \
    git \
    wget \
    unzip

# Install libraries required for GUI and NVIDIA support
RUN apt update && apt install -y --no-install-recommends \
    libglu1-mesa-dev \
    libxcb-xinerama0 \
    libfontconfig1-dev \
    libnvidia-gl-470 \
    libxcb-xkb-dev \
    libxkbcommon-x11-dev \
    libxkbcommon-dev \
    libxcb-xfixes0-dev \
    libxcb-xinput-dev \
    libxcb-xinput0 \
    libpcre2-16-0 \
    libunwind-dev

# Desktop environment + VNC / noVNC / RDP + tooling
# NOTE: do NOT clean /var/lib/apt/lists here; rosdep needs the package index later.
RUN apt update && apt install -y --no-install-recommends \
    xfce4 \
    xfce4-terminal \
    xfce4-settings \
    dbus-x11 \
    x11-xserver-utils \
    tigervnc-standalone-server \
    tigervnc-common \
    novnc \
    websockify \
    xrdp \
    xorgxrdp \
    adwaita-icon-theme \
    tango-icon-theme \
    hicolor-icon-theme \
    librsvg2-common \
    fonts-dejavu-core \
    terminator \
    curl \
    iproute2 \
    procps \
    vim \
    nano \
    dos2unix \
	mesa-utils

# noVNC entry page
RUN ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html

# xrdp needs this to avoid the "connection problem" on root login
RUN adduser xrdp ssl-cert || true

ENV DISPLAY=:1
EXPOSE 5901 6080 3389

# Webots R2025a (pinned .deb release)
# apt is used rather than dpkg -i so the dependency tree resolves automatically.
ARG WEBOTS_VERSION=R2025a
ARG WEBOTS_DEB=webots_2025a_amd64.deb
RUN wget -q --show-progress \
      "https://github.com/cyberbotics/webots/releases/download/${WEBOTS_VERSION}/${WEBOTS_DEB}" \
      -O /tmp/${WEBOTS_DEB} && \
    apt update && \
    apt install -y --no-install-recommends /tmp/${WEBOTS_DEB} && \
    rm -f /tmp/${WEBOTS_DEB}

ENV WEBOTS_HOME=/usr/local/webots
ENV PATH="${WEBOTS_HOME}:${PATH}"

# VirtualGL — redirects GLX calls to the real GPU so OpenGL apps in the VNC
# session get hardware rendering instead of Mesa's llvmpipe.
RUN wget -q https://sourceforge.net/projects/virtualgl/files/3.1/virtualgl_3.1_amd64.deb/download \
      -O /tmp/virtualgl.deb && \
    apt update && \
    apt install -y --no-install-recommends /tmp/virtualgl.deb && \
    rm -f /tmp/virtualgl.deb

ENV PATH="/opt/VirtualGL/bin:${PATH}"

# Copy the RAI repository
COPY . /rai
WORKDIR /rai


RUN mkdir -p /rai/.devcontainer && echo '{ \
  "name": "RAI Dev Container", \
  "build": { \
    "dockerfile": "../docker/Dockerfile", \
    "context": ".." \
  }, \
  "workspaceFolder": "/rai", \
  "customizations": { \
    "vscode": { \
      "extensions": [ \
        "ms-python.python", \
        "ms-ros.ros" \
      ] \
    } \
  }, \
  "runArgs": ["--net=host"] \
}' > /rai/.devcontainer/devcontainer.json

# Defensive: normalize line endings on any script that came from a CRLF checkout
RUN find /rai -maxdepth 2 -name '*.sh' -exec sed -i 's/\r$//' {} +

# Pull ROS source dependencies (rai_interfaces etc.)
RUN apt update && apt install -y --no-install-recommends python3-vcstool && \
    vcs import src < ros_deps.repos

# Ros bridge for webots
RUN apt update && apt install -y --no-install-recommends \
    ros-${ROS_DISTRO}-webots-ros2

ENV USER=root
RUN DRIVER_DIR=/opt/ros/${ROS_DISTRO}/local/lib/python3.10/dist-packages/webots_ros2_driver && \
    sed -i "s/^    return 'microsoft-standard' in uname().release/    return False  # Docker on WSL2 kernel, native Linux Webots/" \
      $DRIVER_DIR/utils.py && \
    rm -rf $DRIVER_DIR/__pycache__

# Install ROS dependencies
RUN /bin/bash -c '. /opt/ros/${ROS_DISTRO}/setup.bash && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y'

# Build the workspace
RUN /bin/bash -c '. /opt/ros/${ROS_DISTRO}/setup.bash && colcon build --symlink-install'

ENV UV_HTTP_TIMEOUT=100
ENV UV_HTTP_RETRIES=10
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100

RUN --mount=type=cache,target=/root/.cache/uv \
    /bin/bash -c 'if [ "${DEPENDENCIES}" = "core_only" ]; then \
      uv sync --locked; \
    else \
      uv sync --locked --all-groups; \
    fi'

# Auto-source ROS 2 setup and local workspace overlay for all interactive bash sessions
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc && \
    echo "source /rai/install/setup.bash" >> ~/.bashrc

COPY docker/entrypoint-desktop.sh /usr/local/bin/entrypoint-desktop.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint-desktop.sh && \
    chmod +x /usr/local/bin/entrypoint-desktop.sh
ENTRYPOINT ["/usr/local/bin/entrypoint-desktop.sh"]
CMD ["bash"]
