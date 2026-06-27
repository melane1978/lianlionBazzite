#!/bin/bash

# Wait for plasmashell to start
for i in {1..30}; do
    PID=$(pgrep -u $USER plasmashell | head -n 1)
    if [ -n "$PID" ]; then
        break
    fi
    sleep 1
done

if [ -z "$PID" ]; then
    echo "[ERROR] plasmashell not found after 30 seconds. Exiting."
    exit 1
fi

# Extract session variables from plasmashell environment
export DISPLAY=$(tr '\0' '\n' < /proc/$PID/environ | grep '^DISPLAY=' | cut -d= -f2-)
export XAUTHORITY=$(tr '\0' '\n' < /proc/$PID/environ | grep '^XAUTHORITY=' | cut -d= -f2-)
export WAYLAND_DISPLAY=$(tr '\0' '\n' < /proc/$PID/environ | grep '^WAYLAND_DISPLAY=' | cut -d= -f2-)

echo "[INFO] Extracted session variables: DISPLAY=$DISPLAY, XAUTHORITY=$XAUTHORITY, WAYLAND_DISPLAY=$WAYLAND_DISPLAY"

# Execute the PyQt6 GUI app inside distrobox
exec distrobox enter lianli-box -- python3 /home/melane/lianlionBazzite/gui_app.py
