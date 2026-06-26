// System Monitor Dashboard - Frontend Logic

// SVG Gauge helper: circumference for r=40 is 2 * pi * 40 ≈ 251.327
const MAX_CIRCUMFERENCE = 251.327;

// Helper to update circular gauges
function updateGauge(fillSelector, valueSelector, val) {
    const fillElement = document.querySelector(fillSelector);
    const valueElement = document.getElementById(valueSelector);
    
    if (fillElement) {
        const offset = MAX_CIRCUMFERENCE - (val / 100) * MAX_CIRCUMFERENCE;
        fillElement.style.strokeDashoffset = offset;
    }
    
    if (valueElement) {
        valueElement.textContent = Math.round(val);
    }
}

// Helper to format bytes per second
function formatSpeed(bytesPerSec) {
    if (bytesPerSec === undefined || isNaN(bytesPerSec)) return "0.0 B/s";
    const k = 1024;
    const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    if (bytesPerSec === 0) return '0.0 B/s';
    const i = Math.floor(Math.log(bytesPerSec) / Math.log(k));
    return parseFloat((bytesPerSec / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Helper to format uptime (seconds to hours and minutes)
function formatUptime(seconds) {
    if (seconds === undefined || isNaN(seconds)) return "0h 0m";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
}

// Update the Swedish clock and date display
function updateClock() {
    const timeElement = document.getElementById('time-val');
    const dateElement = document.getElementById('date-val');
    if (!timeElement || !dateElement) return;

    const now = new Date();
    
    // Format Time: HH:MM:SS
    const timeStr = now.toTimeString().split(' ')[0];
    timeElement.textContent = timeStr;

    // Format Date: FREDAG, 26 JUN
    const weekdays = ['SÖNDAG', 'MÅNDAG', 'TISDAG', 'ONSDAG', 'TORSDAG', 'FREDAG', 'LÖRDAG'];
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAJ', 'JUN', 'JUL', 'AUG', 'SEP', 'OKT', 'NOV', 'DEC'];
    
    const dayName = weekdays[now.getDay()];
    const monthName = months[now.getMonth()];
    const dateNum = now.getDate();
    
    dateElement.textContent = `${dayName}, ${dateNum} ${monthName}`;
}

// Fetch stats from Python server
function fetchStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update CPU
            updateGauge('.cpu-fill', 'cpu-val', data.cpu.usage);
            document.getElementById('cpu-temp').textContent = `${data.cpu.temp.toFixed(1)}°C`;
            
            const coresContainer = document.getElementById('cpu-cores');
            if (coresContainer && data.cpu.cores) {
                coresContainer.innerHTML = data.cpu.cores.map((coreVal, i) => `
                    <div class="core-item">
                        <span class="core-label">C${i + 1}</span>
                        <div class="core-bar">
                            <div class="core-bar-fill" style="width: ${coreVal}%"></div>
                        </div>
                        <span class="core-val">${Math.round(coreVal)}%</span>
                    </div>
                `).join('');
            }
            
            // Update GPU
            updateGauge('.gpu-fill', 'gpu-val', data.gpu.usage);
            document.getElementById('gpu-temp').textContent = `${data.gpu.temp.toFixed(1)}°C`;
            document.getElementById('gpu-vram').textContent = `${data.gpu.mem_used.toFixed(1)} / ${data.gpu.mem_total.toFixed(0)} GB`;

            // Update RAM
            updateGauge('.ram-fill', 'ram-val', data.ram.usage);
            document.getElementById('ram-used').textContent = `${data.ram.used.toFixed(1)} GB`;
            document.getElementById('ram-total').textContent = `${data.ram.total.toFixed(1)} GB`;

            // Update Network & Disk IO
            document.getElementById('net-down').textContent = formatSpeed(data.io.net_download);
            document.getElementById('net-up').textContent = formatSpeed(data.io.net_upload);
            
            const diskContainer = document.getElementById('disk-container');
            if (diskContainer && data.disks) {
                diskContainer.innerHTML = data.disks.map(disk => `
                    <div class="disk-item">
                        <div class="disk-info">
                            <span class="disk-label">${disk.label}</span>
                            <span class="disk-usage-text">${disk.used.toFixed(1)} / ${disk.total.toFixed(0)} GB (${Math.round(disk.percent)}%)</span>
                        </div>
                        <div class="disk-progress-bar">
                            <div class="disk-progress-fill" style="width: ${disk.percent}%"></div>
                        </div>
                    </div>
                `).join('');
            }

            // Update CPU & RAM Processes
            if (data.processes) {
                const cpuProcContainer = document.getElementById('cpu-processes');
                if (cpuProcContainer && data.processes.cpu) {
                    cpuProcContainer.innerHTML = data.processes.cpu.map(p => `
                        <div class="process-item">
                            <span class="proc-name">${p.name}</span>
                            <span class="proc-val">${p.usage.toFixed(1)}%</span>
                        </div>
                    `).join('');
                }
                
                const ramProcContainer = document.getElementById('ram-processes');
                if (ramProcContainer && data.processes.mem) {
                    ramProcContainer.innerHTML = data.processes.mem.map(p => `
                        <div class="process-item">
                            <span class="proc-name">${p.name}</span>
                            <span class="proc-val">${p.usage.toFixed(1)}%</span>
                        </div>
                    `).join('');
                }
            }

            // Update Uptime
            document.getElementById('uptime-val').textContent = formatUptime(data.uptime);
        })
        .catch(err => {
            console.error("Failed to fetch system statistics:", err);
        });
}

// Initial setup and timers
document.addEventListener('DOMContentLoaded', () => {
    // Run clock immediately and then every second
    updateClock();
    setInterval(updateClock, 1000);

    // Fetch stats immediately and then every second
    fetchStats();
    setInterval(fetchStats, 1000);
});
