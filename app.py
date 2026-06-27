import os
import time
import glob
import shutil
import subprocess
from flask import Flask, jsonify, render_template
import psutil

app = Flask(__name__)

# Track historical I/O metrics to calculate speed per second
last_time = time.time()
try:
    disk_io = psutil.disk_io_counters()
    last_disk_read = disk_io.read_bytes if disk_io else 0
    last_disk_write = disk_io.write_bytes if disk_io else 0
except Exception:
    last_disk_read = 0
    last_disk_write = 0

try:
    net_io = psutil.net_io_counters()
    last_net_recv = net_io.bytes_recv if net_io else 0
    last_net_sent = net_io.bytes_sent if net_io else 0
except Exception:
    last_net_recv = 0
    last_net_sent = 0


def get_cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return 0.0
        for name in ['k10temp', 'coretemp', 'zenpower', 'acpitz', 'cpu_thermal']:
            if name in temps:
                for entry in temps[name]:
                    if any(label in entry.label for label in ['Tctl', 'Tdie', 'Package', 'Core']) or entry.label == '':
                        return entry.current
                if temps[name]:
                    return temps[name][0].current
        for name, entries in temps.items():
            if 'cpu' in name.lower():
                for entry in entries:
                    return entry.current
        for entries in temps.values():
            if entries:
                return entries[0].current
    except Exception:
        pass
    return 0.0


def get_nvidia_gpu_stats():
    # Detect if running inside a container
    is_container = os.path.exists('/run/.containerenv') or os.path.exists('/.dockerenv')
    
    if is_container and shutil.which('distrobox-host-exec'):
        cmd = ['distrobox-host-exec', 'nvidia-smi']
    elif shutil.which('nvidia-smi'):
        cmd = ['nvidia-smi']
    else:
        return None
    try:
        res = subprocess.run(
            cmd + ['--query-gpu=name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, check=True
        )
        lines = res.stdout.strip().split('\n')
        if lines and lines[0]:
            parts = [p.strip() for p in lines[0].split(',')]
            if len(parts) >= 6:
                return {
                    'name': parts[0],
                    'temp': float(parts[1]),
                    'usage': float(parts[2]),
                    'mem_usage': float(parts[3]),
                    'mem_used': float(parts[4]),
                    'mem_total': float(parts[5])
                }
    except Exception:
        pass
    return None


def get_amd_gpu_stats():
    amdgpu_paths = glob.glob('/sys/class/drm/card*/device')
    if not amdgpu_paths:
        return None
    
    path = amdgpu_paths[0]
    try:
        stats = {
            'name': 'AMD Radeon GPU',
            'temp': 0.0,
            'usage': 0.0,
            'mem_used': 0.0,
            'mem_total': 0.0,
            'mem_usage': 0.0
        }
        
        # Usage
        busy_path = os.path.join(path, 'gpu_busy_percent')
        if os.path.exists(busy_path):
            with open(busy_path, 'r') as f:
                stats['usage'] = float(f.read().strip())
                
        # VRAM
        used_vram_path = os.path.join(path, 'mem_info_vram_used')
        total_vram_path = os.path.join(path, 'mem_info_vram_total')
        if os.path.exists(used_vram_path) and os.path.exists(total_vram_path):
            with open(used_vram_path, 'r') as f:
                stats['mem_used'] = float(f.read().strip()) / (1024 * 1024)
            with open(total_vram_path, 'r') as f:
                stats['mem_total'] = float(f.read().strip()) / (1024 * 1024)
            if stats['mem_total'] > 0:
                stats['mem_usage'] = (stats['mem_used'] / stats['mem_total']) * 100.0
                
        # Temperature from hwmon
        hwmon_paths = glob.glob(os.path.join(path, 'hwmon/hwmon*'))
        if hwmon_paths:
            temp_path = os.path.join(hwmon_paths[0], 'temp1_input')
            if os.path.exists(temp_path):
                with open(temp_path, 'r') as f:
                    stats['temp'] = float(f.read().strip()) / 1000.0
                    
        return stats
    except Exception:
        pass
    return None


def get_gpu_stats():
    stats = get_nvidia_gpu_stats()
    if stats:
        return stats
    stats = get_amd_gpu_stats()
    if stats:
        return stats
    return {
        'name': 'No Compatible GPU',
        'temp': 0.0,
        'usage': 0.0,
        'mem_usage': 0.0,
        'mem_used': 0.0,
        'mem_total': 0.0
    }


def get_io_speeds():
    global last_time, last_disk_read, last_disk_write, last_net_recv, last_net_sent
    current_time = time.time()
    elapsed = current_time - last_time
    if elapsed <= 0:
        elapsed = 1.0
        
    read_speed = 0.0
    write_speed = 0.0
    recv_speed = 0.0
    sent_speed = 0.0
    
    try:
        disk = psutil.disk_io_counters()
        if disk:
            read_speed = (disk.read_bytes - last_disk_read) / elapsed
            write_speed = (disk.write_bytes - last_disk_write) / elapsed
            last_disk_read = disk.read_bytes
            last_disk_write = disk.write_bytes
    except Exception:
        pass

    try:
        net = psutil.net_io_counters()
        if net:
            recv_speed = (net.bytes_recv - last_net_recv) / elapsed
            sent_speed = (net.bytes_sent - last_net_sent) / elapsed
            last_net_recv = net.bytes_recv
            last_net_sent = net.bytes_sent
    except Exception:
        pass
        
    last_time = current_time
    
    return {
        'disk_read': max(0.0, read_speed),
        'disk_write': max(0.0, write_speed),
        'net_download': max(0.0, recv_speed),
        'net_upload': max(0.0, sent_speed)
    }


cached_disks = []
last_disk_update_time = 0.0

def get_disk_stats():
    global cached_disks, last_disk_update_time
    now = time.time()
    if cached_disks and (now - last_disk_update_time < 300.0):
        return cached_disks

    device_mounts = {}
    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception:
        partitions = []
        
    for p in partitions:
        if not p.device.startswith('/dev/'):
            continue
        if any(x in p.mountpoint for x in ['/containers/storage', '/kubelet', '/flatpak', '/boot', '/dev/pts', '/var/mnt']):
            continue
            
        mount = p.mountpoint
        clean_mount = mount[9:] if mount.startswith('/run/host') else mount
        if not clean_mount:
            clean_mount = '/'
            
        if p.device not in device_mounts:
            device_mounts[p.device] = (p.mountpoint, clean_mount)
        else:
            curr = device_mounts[p.device][1]
            if clean_mount == '/' or (len(clean_mount) < len(curr) and not clean_mount.startswith('/run/host')):
                device_mounts[p.device] = (p.mountpoint, clean_mount)
                
    disks = []
    for device, (raw_mount, clean_mount) in device_mounts.items():
        try:
            usage = psutil.disk_usage(raw_mount)
            label = clean_mount.split('/')[-1]
            if not label or label.lower() in ['etc', 'sysroot', 'host', 'run']:
                label = 'System'
                clean_mount = '/'
            disks.append({
                'label': label.upper(),
                'mount': clean_mount,
                'total': usage.total / (1024 * 1024 * 1024),
                'used': usage.used / (1024 * 1024 * 1024),
                'percent': usage.percent
            })
        except Exception:
            pass
            
    # Fallback to single System disk if empty
    if not disks:
        try:
            usage = psutil.disk_usage('/')
            disks.append({
                'label': 'SYSTEM',
                'mount': '/',
                'total': usage.total / (1024 * 1024 * 1024),
                'used': usage.used / (1024 * 1024 * 1024),
                'percent': usage.percent
            })
        except Exception:
            pass
            
    cached_disks = disks
    last_disk_update_time = now
    return disks


cached_processes = {'cpu': [], 'mem': []}
last_proc_update = 0.0

def get_top_processes():
    global cached_processes, last_proc_update
    now = time.time()
    if cached_processes['cpu'] and (now - last_proc_update < 3.0):
        return cached_processes
        
    processes = []
    for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            # Filter out system idling/kernel processes to make list meaningful
            if info['name'] in ['System Idle Process', 'idle', 'ksoftirqd', 'kworker'] or 'kworker' in info['name']:
                continue
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    # Sort by usage and take top 3
    top_cpu = sorted([p for p in processes if p['cpu_percent'] is not None], key=lambda x: x['cpu_percent'], reverse=True)[:3]
    top_mem = sorted([p for p in processes if p['memory_percent'] is not None], key=lambda x: x['memory_percent'], reverse=True)[:3]
    
    num_cores = psutil.cpu_count() or 1
    cached_processes = {
        'cpu': [{'name': p['name'], 'usage': p['cpu_percent'] / num_cores} for p in top_cpu],
        'mem': [{'name': p['name'], 'usage': p['memory_percent']} for p in top_mem]
    }
    last_proc_update = now
    return cached_processes


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stats')
def api_stats():
    cpu_usage = psutil.cpu_percent()
    cpu_temp = get_cpu_temp()
    cpu_cores = psutil.cpu_percent(percpu=True)
    
    virtual_mem = psutil.virtual_memory()
    ram_used = virtual_mem.used / (1024 * 1024 * 1024)
    ram_total = virtual_mem.total / (1024 * 1024 * 1024)
    ram_usage = virtual_mem.percent
    
    gpu = get_gpu_stats()
    io = get_io_speeds()
    disks = get_disk_stats()
    processes = get_top_processes()
    
    uptime = time.time() - psutil.boot_time()

    return jsonify({
        'cpu': {
            'usage': cpu_usage,
            'temp': cpu_temp,
            'cores': cpu_cores
        },
        'gpu': gpu,
        'ram': {
            'used': ram_used,
            'total': ram_total,
            'usage': ram_usage
        },
        'io': io,
        'disks': disks,
        'uptime': uptime,
        'processes': processes
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
