# Network Discovery Examples

Scan networks and discover devices with AI-powered queries.

## 📁 Examples

| File | Description |
|------|-------------|
| [network_discovery.py](network_discovery.py) | Scan and find devices |
| [camera_finder.py](camera_finder.py) | Find all cameras on network |
| [smart_camera_monitor.py](smart_camera_monitor.py) | **Auto-discover + analyze cameras** |
| [security_pipeline.py](security_pipeline.py) | **Complete security monitoring pipeline** |

---

## 🚀 Quick Start

```bash
# Scan entire network (YAML output - default)
sq network scan

# Scan with different formats
sq network scan --yaml     # YAML (default)
sq network scan --json     # JSON
sq network scan --table    # ASCII table

# Scan specific subnet
sq network scan --subnet 192.168.1.0/24

# Find Raspberry Pi devices
sq network find "raspberry pi"

# Find cameras
sq network find "cameras"

# Find printers
sq network find "printers"

# Find IoT devices
sq network find "smart home devices"

# Identify specific device
sq network identify --ip 192.168.1.100

# Scan ports
sq network ports --ip 192.168.1.100
```

## 📊 Output Formats

```bash
# YAML (default)
sq network scan --yaml
# Output:
# camera:
#   - ip: 192.168.1.100
#     mac: "28:87:BA:0D:31:D6"

# JSON
sq network scan --json
# Output: {"devices": [...], "by_type": {...}}

# ASCII Table
sq network scan --table
# Output:
# +-----------------+-------------+-------------------+
# | IP              | Hostname    | Type              |
# +=================+=============+===================+
# | 192.168.1.100   | cam-garage  | IP Camera         |
```

---

## 📡 Supported Device Types

| Type | Detection Method | Icon |
|------|-----------------|------|
| Raspberry Pi | MAC prefix (B8:27:EB, DC:A6:32) | 🍓 |
| Camera | MAC + ports (554, 8080) | 📷 |
| Printer | MAC + ports (9100, 631) | 🖨️ |
| Router | MAC + hostname | 📡 |
| NAS | MAC (Synology, QNAP) + ports | 💾 |
| Smart TV | MAC + ports (8008) | 📺 |
| IoT Device | ESP8266/ESP32 MAC prefix | 🏠 |
| Server | Ports (22, 80, 443, DBs) | 🖥️ |

---

## 💻 Python API

```python
from streamware import flow
from streamware.components.network_scan import (
    scan_network,
    find_devices,
    find_cameras,
    find_raspberry_pi,
    find_printers,
)

# Full network scan
result = scan_network()
for device in result["devices"]:
    print(f"{device['ip']} - {device['description']}")

# Find specific devices
cameras = find_cameras()
print(f"Found {len(cameras['devices'])} cameras")

rpis = find_raspberry_pi()
for rpi in rpis["devices"]:
    print(f"Raspberry Pi at {rpi['ip']}")

# Natural language query
result = find_devices("all smart home devices")
result = find_devices("servers with SSH")
result = find_devices("printers")

# Using flow API
result = flow("network://find?query=cameras").run()
result = flow("network://identify?ip=192.168.1.100").run()
```

---

## 🔧 Requirements

```bash
# For best results, install these:
sudo apt-get install nmap arp-scan

# For LLM-based queries:
ollama pull qwen2.5:14b
```

---

## 📚 Related

| Resource | Description |
|----------|-------------|
| [Stream Analysis](../media-processing/) | Analyze camera streams |
| [Automation](../automation/) | Automate based on devices |
| [Source Code](../../streamware/components/network_scan.py) | Implementation |

---

## 📋 Use Cases

### 1. Security Audit

```bash
# Find all cameras and check their ports
sq network find "cameras" | jq '.devices[] | {ip, ports}'
```

### 2. IoT Inventory

```bash
# List all IoT devices
sq network find "IoT devices"
```

### 3. Raspberry Pi Cluster Management

```bash
# Find all Pis for cluster
sq network find "raspberry pi" | jq '.devices[].ip'
```

### 4. Printer Discovery

```bash
# Find printers for setup
sq network find "printers"
```

### 5. Camera + Stream Analysis Pipeline

```bash
# Find cameras and analyze one
CAMERAS=$(sq network find "cameras" --quiet | jq -r '.devices[0].ip')
sq stream rtsp --url "rtsp://$CAMERAS/live" --mode diff
```

---

## 🔗 Multi-Component Pipelines

### Auto-discover and Monitor Cameras

```bash
# Python: Full pipeline
python smart_camera_monitor.py

# CLI equivalent:
# Step 1: Find cameras
sq network find "cameras" --yaml

# Step 2: Get RTSP URL from output
# camera:
#   - ip: 192.168.1.1
#     vendor: Reolink
#     rtsp:
#       - "rtsp://192.168.1.100:554/h264Preview_01_main"
#     credentials: "admin/admin123"

# Step 3: Analyze stream
sq stream rtsp --url "rtsp://admin:admin123@192.168.1.100:554/h264Preview_01_main" --mode diff --interval 5
```

### Security Monitoring Pipeline

```bash
# Full security pipeline with alerts
python security_pipeline.py --watch --interval 60

# Or step by step:

# 1. Discover all network devices
sq network scan --yaml

# 2. Find cameras specifically  
sq network find "cameras" --yaml

# 3. Monitor each camera
sq stream rtsp --url "rtsp://admin:admin123@192.168.1.100:554/h264Preview_01_main" --mode diff --continuous

# 4. On activity, send alert (example with Slack)
sq slack alerts --message "Motion detected on camera 192.168.1.100"
```

### Bash Pipeline Example

```bash
#!/bin/bash
# auto_camera_monitor.sh - Find and monitor all cameras

echo "🔍 Discovering cameras..."
CAMERAS=$(sq network find "cameras" --json 2>/dev/null | jq -r '.devices[]')

echo "$CAMERAS" | jq -r '.ip + ":" + .connection.rtsp[0]' | while read line; do
    IP=$(echo "$line" | cut -d: -f1)
    RTSP=$(echo "$line" | cut -d: -f2-)
    
    echo "📷 Monitoring $IP..."
    sq stream rtsp --url "$RTSP" --mode diff --duration 30
done
```

### Python Pipeline Example

```python
from streamware import flow
from streamware.components.network_scan import find_cameras

# Step 1: Find cameras
result = find_cameras()
cameras = result.get("devices", [])

# Step 2: Analyze each camera
for cam in cameras:
    ip = cam["ip"]
    rtsp = cam.get("connection", {}).get("rtsp", [])[0]
    
    print(f"Analyzing {ip}...")
    
    analysis = flow(f"stream://rtsp?url={rtsp}&mode=diff&duration=30").run()
    
    if analysis.get("significant_changes", 0) > 0:
        print(f"🔴 Activity detected on {ip}!")
        
        # Send alert via Slack
        flow(f"slack://alerts?message=Motion on {ip}").run()
```
