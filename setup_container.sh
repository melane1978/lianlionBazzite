#!/bin/bash
# Shell script to automate rebuilding and setting up the lianli-box container.

set -e

echo "==> Creating distrobox 'lianli-box' using distrobox.ini..."
distrobox assemble create --file distrobox.ini

echo "==> Checking and installing yay (AUR helper)..."
distrobox enter lianli-box -- sh -c "if ! command -v yay &> /dev/null; then git clone https://aur.archlinux.org/yay-bin.git && cd yay-bin && makepkg -si --noconfirm && cd .. && rm -rf yay-bin; fi"

echo "==> Installing lianli-linux-git from AUR..."
distrobox enter lianli-box -- yay -S --needed --noconfirm lianli-linux-git

echo "==> Setting up systemd user service..."
mkdir -p ~/.config/systemd/user/
cp config/sensor-panel.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now sensor-panel.service

echo "==> Setting up autostart desktop entry..."
mkdir -p ~/.config/autostart/
cp config/sensor-panel-gui.desktop ~/.config/autostart/

echo "==> Copying Lian Li & EVDI udev rules (requires sudo)..."
sudo cp config/99-lianli.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "==> Setting up evdi module configuration to pre-create display device (requires sudo)..."
sudo cp config/evdi.conf /etc/modprobe.d/

echo "==> Done! The sensor panel service has been started, and autostart is enabled."
