# Lian Li 8.8" Custom Sensor Dashboard for Bazzite

This project is a custom system monitor dashboard designed specifically for a **8.8" Lian Li screen (480x1920 / 480x1980 pixels)** running in portrait orientation.

The dashboard runs on **Bazzite OS (Fedora Silverblue base)**. To maintain a clean host system, the monitoring server executes inside an isolated **Arch Linux Distrobox container (`lianli-box`)**. The interface is displayed in a frameless window via a PyQt6 WebEngine wrapper (forcing the X11/xcb platform plugin to ensure absolute screen positioning under Wayland).

---

## 🚀 Features

- **💻 CPU Monitoring:** Shows overall CPU load (circular gauge), temperature, and a real-time grid view of **individual logical core usage** (12 cores total).
- **🎮 GPU Monitoring:** Shows load, temperature, and VRAM utilization for your **NVIDIA GeForce RTX 3060**. Since the container runs rootless, it automatically calls the host's `nvidia-smi` utility via `distrobox-host-exec` to avoid driver library mapping issues.
- **⚡ RAM Monitoring:** Shows used vs. total memory in gigabytes and a minified percentage circular gauge.
- **💾 Disk Monitoring:** Dynamically detects and lists all physical storage drives (SYSTEM, STEAM, MEDIA, etc.) with space details and progress bars. Disk usage statistics are cached for 5 minutes to prevent system stutter when disks spin down.
- **🔝 Top Processes:** Lists the top 3 processes by CPU and RAM consumption. CPU process usage is **scaled (0-100%)** based on total logical core count (similar to Windows Task Manager).
- **⏱️ Clock & Uptime:** Displays current time and date in Swedish, along with system uptime.
- **🖼️ Premium Aesthetics:** Dark glassmorphic design system with harmonized neon glow colors matching each card's theme.

---

## 🛠️ Setup & Installation

The configuration files and scripts are packaged to automate the setup process.

### 1. Clone the repository
Clone this repository to your user's home folder:
```bash
cd ~
git clone git@github.com:melane1978/lianlionBazzite.git
cd lianlionBazzite
```

### 2. Run the setup script
Make the setup script executable and run it. This script will automatically create the Distrobox container, install all system packages, fetch AUR dependencies (`lianli-linux-git` using `yay`), copy the Lian Li & EVDI udev rules to the host `/etc/udev/rules.d/` (requires `sudo` access), and install the required configuration files:
```bash
chmod +x setup_container.sh
./setup_container.sh
```

---

## ⚙️ How to Manage the Dashboard

### The Backend Service (Flask API)
The monitoring server runs as a systemd user service and starts automatically upon user login:
- **Start:** `systemctl --user start sensor-panel.service`
- **Stop:** `systemctl --user stop sensor-panel.service`
- **Restart:** `systemctl --user restart sensor-panel.service`
- **Status:** `systemctl --user status sensor-panel.service`

### The GUI Application (PyQt6)
The GUI window wrapper starts automatically on desktop login via KDE/GNOME Autostart. It:
1. Scans all connected displays.
2. Auto-detects the display matching the Lian Li aspect ratio (4:1 or 1:4).
3. Positions itself to cover the target screen in a frameless window.

#### Keyboard Shortcuts & Interaction:
- **Right-click on the dashboard:** Opens a dark context menu to *Minimize*, *Reload (F5)*, or *Close*.
- **F5:** Reloads the dashboard.
- **Esc:** Minimizes the window.
- **System Tray Icon:** A computer monitor icon is placed in your desktop system tray (next to the clock). Click it to toggle the visibility of the sensor panel.

---

## 📁 Project Structure

- `app.py` - Flask backend service returning system metrics JSON.
- `gui_app.py` - PyQt6 window wrapper rendering the web interface.
- `distrobox.ini` - Declarative definition of the Distrobox container environment.
- `setup_container.sh` - Automation script for setting up the container, configuring udev rules, and copying configs.
- `config/` - Backups of the systemd service, autostart `.desktop` files, `99-lianli.rules` (udev rules for EVDI permissions), and `evdi.conf` (pre-creates the virtual display card at boot to resolve container mapping timing issues).
- `templates/index.html` - HTML layout for the dashboard.
- `static/css/style.css` - CSS styles (glassmorphism, layouts, and neon accents).
- `static/js/main.js` - JS frontend logic for polling the API and updating elements.
