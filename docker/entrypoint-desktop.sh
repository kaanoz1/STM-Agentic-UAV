#!/bin/bash
set -e

VNC_GEOMETRY="${VNC_GEOMETRY:-1920x1080}"
VNC_DISPLAY="${VNC_DISPLAY:-:1}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
VNC_PORT="${VNC_PORT:-5901}"

# No authentication. VNC listens on the container's loopback only; the desktop
# is reached through noVNC on $NOVNC_PORT.

VNCSERVER="$(command -v tigervncserver || command -v vncserver || true)"

if [ -z "$VNCSERVER" ]; then
    echo "ERROR: no tigervncserver/vncserver binary found." >&2
    ls /usr/bin | grep -i vnc >&2 || echo "  (no vnc binaries at all)" >&2
    exit 1
fi

echo ">> using $VNCSERVER"

# ---------------------------------------------------------- XFCE session --
mkdir -p /root/.vnc
cat > /root/.vnc/xstartup << 'XSTARTUP'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec dbus-launch startxfce4
XSTARTUP
chmod +x /root/.vnc/xstartup
cp /root/.vnc/xstartup /root/.xsession
chmod +x /root/.xsession

# -------------------------------------------------------------- VNC server --
"$VNCSERVER" -kill "$VNC_DISPLAY" >/dev/null 2>&1 || true
rm -f "/tmp/.X11-unix/X${VNC_DISPLAY#:}" "/tmp/.X${VNC_DISPLAY#:}-lock"

"$VNCSERVER" "$VNC_DISPLAY" \
    -geometry "$VNC_GEOMETRY" \
    -depth 24 \
    -localhost yes \
    -SecurityTypes None \
    --I-KNOW-THIS-IS-INSECURE \
    -xstartup /root/.vnc/xstartup

# ---------------------------------------------------------------- noVNC --
# setsid puts websockify in its own session so Ctrl+C in an attached shell
# cannot kill it.
setsid nohup websockify \
    --web=/usr/share/novnc \
    "$NOVNC_PORT" "localhost:${VNC_PORT}" \
    > /var/log/websockify.log 2>&1 &

novnc_up=0
for _ in $(seq 1 20); do
    if curl -sf -o /dev/null "http://localhost:${NOVNC_PORT}/vnc.html"; then
        novnc_up=1
        break
    fi
    sleep 0.5
done

if [ "$novnc_up" = "1" ]; then
    echo ">> noVNC serving on ${NOVNC_PORT}"
else
    echo "WARNING: noVNC did not come up on ${NOVNC_PORT}. websockify log:" >&2
    cat /var/log/websockify.log >&2 || true
fi

# ------------------------------------------------------------------- RDP --
service dbus start >/dev/null 2>&1 || true
setsid /usr/sbin/xrdp-sesman > /var/log/xrdp-sesman.log 2>&1 \
    || echo ">> xrdp-sesman failed to start, RDP unavailable" >&2
setsid /usr/sbin/xrdp > /var/log/xrdp.log 2>&1 \
    || echo ">> xrdp failed to start, RDP unavailable" >&2

# --------------------------------------------------------- ROS environment --
set +e
source "/opt/ros/${ROS_DISTRO}/setup.bash"
[ -f /rai/install/setup.bash ] && source /rai/install/setup.bash
set -e

echo ">> desktop ready (no password)"
echo ">>   browser : http://localhost:${NOVNC_PORT}/vnc.html"
echo ">>   logs    : /var/log/websockify.log /var/log/xrdp.log /root/.vnc/*.log"

exec "$@"
