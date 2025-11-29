"""
Network Scan Component - Discover devices on network with AI queries

Supported operations:
    - scan: Scan network for devices
    - find: Find specific device types using LLM
    - identify: Identify device by IP/MAC
    - monitor: Monitor network for new devices

URI Examples:
    network://scan?subnet=192.168.1.0/24
    network://find?query=cameras&subnet=192.168.1.0/24
    network://find?query=raspberry pi
    network://identify?ip=192.168.1.100

CLI:
    sq network scan --subnet 192.168.1.0/24
    sq network find "all cameras"
    sq network find "raspberry pi devices"
    sq network find "printers"

Related:
    - examples/network/network_discovery.py
    - streamware/components/stream.py (for camera integration)
"""

import subprocess
import socket
import logging
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..core import Component, StreamwareURI, register
from ..exceptions import ComponentError
from ..config import config

logger = logging.getLogger(__name__)


# MAC Prefix to Vendor database (expanded)
MAC_VENDORS = {
    # Cameras
    "28:87:BA": {"vendor": "Reolink", "type": "camera"},
    "EC:71:DB": {"vendor": "Reolink", "type": "camera"},  # Also Reolink!
    "AC:CC:8E": {"vendor": "Hikvision", "type": "camera"},
    "C0:56:E3": {"vendor": "Hikvision", "type": "camera"},
    "54:C4:15": {"vendor": "Hikvision", "type": "camera"},
    "44:19:B6": {"vendor": "Hikvision", "type": "camera"},
    "A4:14:37": {"vendor": "Dahua", "type": "camera"},
    "3C:EF:8C": {"vendor": "Dahua", "type": "camera"},
    "E0:50:8B": {"vendor": "Dahua", "type": "camera"},
    "00:80:F0": {"vendor": "Axis", "type": "camera"},
    "00:40:8C": {"vendor": "Axis", "type": "camera"},
    "B8:A4:4F": {"vendor": "Axis", "type": "camera"},
    "00:0F:7C": {"vendor": "ACTi", "type": "camera"},
    "00:18:AE": {"vendor": "TVT", "type": "camera"},
    "70:B3:D5": {"vendor": "Ubiquiti", "type": "camera"},
    "FC:EC:DA": {"vendor": "Ubiquiti", "type": "camera"},
    "24:5A:4C": {"vendor": "Ubiquiti", "type": "camera"},
    "78:8A:20": {"vendor": "Ubiquiti", "type": "camera"},
    "E8:48:B8": {"vendor": "TP-Link", "type": "camera"},
    "50:C7:BF": {"vendor": "TP-Link", "type": "camera"},
    "5C:A6:E6": {"vendor": "TP-Link", "type": "camera"},
    "B0:BE:76": {"vendor": "TP-Link", "type": "camera"},
    "14:EB:B6": {"vendor": "TP-Link", "type": "camera"},
    "C4:E9:84": {"vendor": "TP-Link", "type": "camera"},
    "60:32:B1": {"vendor": "TP-Link", "type": "camera"},
    "98:DA:C4": {"vendor": "TP-Link", "type": "camera"},
    "D8:0D:17": {"vendor": "TP-Link", "type": "camera"},
    "F0:9F:C2": {"vendor": "Ubiquiti", "type": "camera"},
    "78:45:58": {"vendor": "Ubiquiti", "type": "camera"},
    "68:72:51": {"vendor": "Ubiquiti", "type": "camera"},
    "B4:FB:E4": {"vendor": "Ubiquiti", "type": "camera"},
    "E0:63:DA": {"vendor": "Ubiquiti", "type": "camera"},
    "04:18:D6": {"vendor": "Ubiquiti", "type": "camera"},
    "DC:9F:DB": {"vendor": "Ubiquiti", "type": "camera"},
    "74:AC:B9": {"vendor": "Ubiquiti", "type": "camera"},
    "24:A4:3C": {"vendor": "Ubiquiti", "type": "camera"},
    "80:2A:A8": {"vendor": "Ubiquiti", "type": "camera"},
    
    # Printers
    "3C:2A:F4": {"vendor": "Brother", "type": "printer"},
    "00:1B:A9": {"vendor": "Brother", "type": "printer"},
    "00:80:77": {"vendor": "Brother", "type": "printer"},
    "30:CD:A7": {"vendor": "Brother", "type": "printer"},
    "00:00:48": {"vendor": "HP", "type": "printer"},
    "00:17:08": {"vendor": "HP", "type": "printer"},
    "00:1E:0B": {"vendor": "HP", "type": "printer"},
    "3C:D9:2B": {"vendor": "HP", "type": "printer"},
    "10:60:4B": {"vendor": "HP", "type": "printer"},
    "94:57:A5": {"vendor": "HP", "type": "printer"},
    "48:0F:CF": {"vendor": "HP", "type": "printer"},
    "00:00:85": {"vendor": "Canon", "type": "printer"},
    "00:1E:8F": {"vendor": "Canon", "type": "printer"},
    "18:0C:AC": {"vendor": "Canon", "type": "printer"},
    "84:25:19": {"vendor": "Canon", "type": "printer"},
    "00:26:AB": {"vendor": "Epson", "type": "printer"},
    "00:1B:81": {"vendor": "Epson", "type": "printer"},
    "64:EB:8C": {"vendor": "Epson", "type": "printer"},
    "48:65:EE": {"vendor": "Epson", "type": "printer"},
    
    # Raspberry Pi
    "B8:27:EB": {"vendor": "Raspberry Pi Foundation", "type": "raspberry_pi"},
    "DC:A6:32": {"vendor": "Raspberry Pi Foundation", "type": "raspberry_pi"},
    "E4:5F:01": {"vendor": "Raspberry Pi Foundation", "type": "raspberry_pi"},
    "28:CD:C1": {"vendor": "Raspberry Pi Foundation", "type": "raspberry_pi"},
    "D8:3A:DD": {"vendor": "Raspberry Pi Foundation", "type": "raspberry_pi"},
    
    # Routers
    "68:1D:EF": {"vendor": "TP-Link", "type": "router"},
    "14:CC:20": {"vendor": "TP-Link", "type": "router"},
    "EC:08:6B": {"vendor": "TP-Link", "type": "router"},
    "00:1A:2B": {"vendor": "Cisco/Linksys", "type": "router"},
    "00:1D:7E": {"vendor": "Cisco/Linksys", "type": "router"},
    "C8:3A:35": {"vendor": "Netgear", "type": "router"},
    "B0:7F:B9": {"vendor": "Netgear", "type": "router"},
    "84:1B:5E": {"vendor": "Netgear", "type": "router"},
    "9C:3D:CF": {"vendor": "Netgear", "type": "router"},
    "20:0C:C8": {"vendor": "Netgear", "type": "router"},
    "C4:04:15": {"vendor": "ASUS", "type": "router"},
    "F8:32:E4": {"vendor": "ASUS", "type": "router"},
    "E0:3F:49": {"vendor": "ASUS", "type": "router"},
    "10:C3:7B": {"vendor": "ASUS", "type": "router"},
    "04:D4:C4": {"vendor": "ASUS", "type": "router"},
    "24:4B:FE": {"vendor": "ASUS", "type": "router"},
    
    # NAS
    "00:11:32": {"vendor": "Synology", "type": "nas"},
    "00:90:A9": {"vendor": "QNAP", "type": "nas"},
    "24:5E:BE": {"vendor": "QNAP", "type": "nas"},
    
    # IoT / ESP
    "18:FE:34": {"vendor": "Espressif (ESP8266)", "type": "iot_device"},
    "60:01:94": {"vendor": "Espressif (ESP32)", "type": "iot_device"},
    "A0:20:A6": {"vendor": "Espressif", "type": "iot_device"},
    "AC:CF:23": {"vendor": "Espressif (ESP32-C3)", "type": "iot_device"},
    "E8:A0:ED": {"vendor": "Espressif", "type": "iot_device"},
    "24:6F:28": {"vendor": "Espressif (ESP32)", "type": "iot_device"},
    "30:AE:A4": {"vendor": "Espressif", "type": "iot_device"},
    "84:CC:A8": {"vendor": "Espressif", "type": "iot_device"},
    "A4:CF:12": {"vendor": "Espressif", "type": "iot_device"},
    "BC:DD:C2": {"vendor": "Espressif", "type": "iot_device"},
    "C4:4F:33": {"vendor": "Espressif", "type": "iot_device"},
    "CC:50:E3": {"vendor": "Espressif", "type": "iot_device"},
    "D8:F1:5B": {"vendor": "Espressif", "type": "iot_device"},
    "EC:FA:BC": {"vendor": "Espressif", "type": "iot_device"},
    
    # Smart TV
    "00:12:FB": {"vendor": "Samsung TV", "type": "smart_tv"},
    "5C:49:7D": {"vendor": "Samsung TV", "type": "smart_tv"},
    "78:BD:BC": {"vendor": "Samsung TV", "type": "smart_tv"},
    "F4:7B:5E": {"vendor": "Samsung TV", "type": "smart_tv"},
}

# Default RTSP paths and connection info by vendor
VENDOR_CONNECTION_INFO = {
    "Reolink": {
        "rtsp_paths": [
            "rtsp://{ip}:554/h264Preview_01_main",
            "rtsp://{ip}:554/h264Preview_01_sub",
            "rtsp://{user}:{pass}@{ip}:554/h264Preview_01_main",
        ],
        "default_user": "admin",
        "default_pass": "admin123",
        "web_port": 80,
        "notes": "Default credentials: admin/admin123 or admin/password"
    },
    "Hikvision": {
        "rtsp_paths": [
            "rtsp://{user}:{pass}@{ip}:554/Streaming/Channels/101",
            "rtsp://{user}:{pass}@{ip}:554/Streaming/Channels/102",
            "rtsp://{ip}:554/h264/ch1/main/av_stream",
        ],
        "default_user": "admin",
        "default_pass": "12345",
        "web_port": 80,
        "notes": "Default: admin/12345. 101=main, 102=sub stream"
    },
    "Dahua": {
        "rtsp_paths": [
            "rtsp://{user}:{pass}@{ip}:554/cam/realmonitor?channel=1&subtype=0",
            "rtsp://{user}:{pass}@{ip}:554/cam/realmonitor?channel=1&subtype=1",
        ],
        "default_user": "admin",
        "default_pass": "admin",
        "web_port": 80,
        "notes": "Default: admin/admin. subtype=0 main, subtype=1 sub"
    },
    "Axis": {
        "rtsp_paths": [
            "rtsp://{ip}/axis-media/media.amp",
            "rtsp://{user}:{pass}@{ip}/axis-media/media.amp",
        ],
        "default_user": "root",
        "default_pass": "pass",
        "web_port": 80,
        "notes": "Default: root/pass or admin/admin"
    },
    "Ubiquiti": {
        "rtsp_paths": [
            "rtsp://{ip}:7447/",
            "rtsps://{ip}:7441/",
        ],
        "default_user": "ubnt",
        "default_pass": "ubnt",
        "web_port": 7080,
        "notes": "UniFi Protect cameras. Default: ubnt/ubnt"
    },
    "TP-Link": {
        "rtsp_paths": [
            "rtsp://{user}:{pass}@{ip}:554/stream1",
            "rtsp://{user}:{pass}@{ip}:554/stream2",
            "rtsp://{ip}:554/h264_hd.sdp",
        ],
        "default_user": "admin",
        "default_pass": "admin",
        "web_port": 80,
        "notes": "Tapo cameras: admin/<cloud_password>"
    },
    "ACTi": {
        "rtsp_paths": [
            "rtsp://{user}:{pass}@{ip}/",
        ],
        "default_user": "Admin",
        "default_pass": "123456",
        "web_port": 80,
        "notes": "Default: Admin/123456"
    },
    "Brother": {
        "print_url": "socket://{ip}:9100",
        "ipp_url": "ipp://{ip}:631/ipp/print",
        "web_port": 80,
        "notes": "JetDirect: port 9100, IPP: port 631"
    },
    "HP": {
        "print_url": "socket://{ip}:9100",
        "ipp_url": "ipp://{ip}:631/ipp/print",
        "web_port": 80,
        "notes": "JetDirect: port 9100, Web UI: http://{ip}"
    },
    "Canon": {
        "print_url": "socket://{ip}:9100",
        "ipp_url": "ipp://{ip}:631/ipp/print",
        "web_port": 80,
        "notes": "Remote UI: http://{ip}"
    },
    "Epson": {
        "print_url": "socket://{ip}:9100",
        "ipp_url": "ipp://{ip}:631/ipp/print",
        "web_port": 80,
        "notes": "Epson Connect: http://{ip}"
    },
    "Synology": {
        "web_port": 5000,
        "https_port": 5001,
        "ssh_port": 22,
        "notes": "DSM: http://{ip}:5000 or https://{ip}:5001"
    },
    "QNAP": {
        "web_port": 8080,
        "https_port": 443,
        "ssh_port": 22,
        "notes": "QTS: http://{ip}:8080"
    },
}

# Known device signatures (MAC prefixes and characteristics)
DEVICE_SIGNATURES = {
    "raspberry_pi": {
        "mac_prefixes": ["B8:27:EB", "DC:A6:32", "E4:5F:01", "28:CD:C1", "D8:3A:DD"],
        "hostnames": ["raspberry", "raspberrypi", "rpi"],
        "ports": [22],
        "port_signature": {22},
        "description": "Raspberry Pi"
    },
    "camera": {
        "mac_prefixes": ["28:87:BA", "EC:71:DB", "AC:CC:8E", "C0:56:E3", "54:C4:15", "44:19:B6",
                        "A4:14:37", "3C:EF:8C", "E0:50:8B", "00:80:F0", "00:40:8C", "B8:A4:4F",
                        "00:0F:7C", "00:18:AE", "70:B3:D5", "FC:EC:DA", "24:5A:4C", "78:8A:20",
                        "E8:48:B8", "50:C7:BF", "5C:A6:E6"],
        "hostnames": ["cam", "camera", "ipcam", "hikvision", "dahua", "axis", "reolink", "unifi"],
        "ports": [80, 443, 554, 8080, 8554, 7447],
        "port_signature": {554, 7447},
        "description": "IP Camera"
    },
    "printer": {
        "mac_prefixes": ["3C:2A:F4", "00:1B:A9", "00:80:77", "30:CD:A7", "00:00:48", "00:17:08",
                        "00:1E:0B", "3C:D9:2B", "10:60:4B", "00:00:85", "00:1E:8F", "00:26:AB"],
        "hostnames": ["printer", "hp", "epson", "canon", "brother", "xerox"],
        "ports": [9100, 515, 631],
        "port_signature": {9100, 631},
        "description": "Network Printer"
    },
    "router": {
        "mac_prefixes": ["68:1D:EF", "14:CC:20", "EC:08:6B", "00:1A:2B", "00:1D:7E",
                        "C8:3A:35", "B0:7F:B9", "C4:04:15", "F8:32:E4"],
        "hostnames": ["router", "gateway", "_gateway", "ap", "wifi", "access", "fritz"],
        "ports": [80, 443, 22, 23, 53],
        "port_signature": {53},
        "description": "Router / Access Point"
    },
    "nas": {
        "mac_prefixes": ["00:11:32", "00:90:A9", "24:5E:BE"],
        "hostnames": ["nas", "synology", "qnap", "storage", "fileserver", "diskstation"],
        "ports": [5000, 5001, 445, 139, 22, 8080],
        "port_signature": {5000, 445},
        "description": "NAS Storage"
    },
    "smart_tv": {
        "mac_prefixes": ["00:12:FB", "5C:49:7D", "78:BD:BC", "F4:7B:5E"],
        "hostnames": ["tv", "samsung", "lg", "sony", "roku", "firetv", "chromecast", "androidtv"],
        "ports": [8008, 8443, 9080, 8009],
        "port_signature": {8008, 8009},
        "description": "Smart TV / Media"
    },
    "iot_device": {
        "mac_prefixes": ["18:FE:34", "60:01:94", "A0:20:A6", "AC:CF:23", "E8:A0:ED",
                        "24:6F:28", "30:AE:A4", "84:CC:A8", "A4:CF:12", "BC:DD:C2"],
        "hostnames": ["esp", "tasmota", "sonoff", "shelly", "tuya", "smart", "plug"],
        "ports": [80, 8080],
        "port_signature": set(),
        "description": "IoT Device"
    },
    "gpu_server": {
        "mac_prefixes": [],
        "hostnames": ["nvidia", "gpu", "cuda", "ml", "ai", "deep", "tensor"],
        "ports": [22, 8888, 6006, 5000],
        "port_signature": {8888, 6006},
        "description": "GPU/ML Server"
    },
    "server": {
        "mac_prefixes": [],
        "hostnames": ["server", "srv", "host", "node", "linux", "ubuntu", "debian", "centos"],
        "ports": [22, 80, 443, 3306, 5432, 6379, 27017],
        "port_signature": {3306, 5432, 6379},
        "description": "Server"
    },
    "workstation": {
        "mac_prefixes": [],
        "hostnames": ["pc", "desktop", "workstation", "win", "mac", "imac"],
        "ports": [22, 3389, 5900],
        "port_signature": {3389, 5900},
        "description": "Workstation/PC"
    },
    "mobile": {
        "mac_prefixes": [],
        "hostnames": ["iphone", "android", "phone", "mobile", "galaxy", "pixel", "ipad"],
        "ports": [],
        "port_signature": set(),
        "description": "Mobile Device"
    },
}


@register("network")
@register("netscan")
@register("discover")
class NetworkScanComponent(Component):
    """
    Network scanning and device discovery component.
    
    Operations:
        - scan: Full network scan
        - find: Find devices by type using LLM
        - identify: Identify single device
        - monitor: Watch for new devices
    
    URI Examples:
        network://scan?subnet=192.168.1.0/24
        network://find?query=cameras
        network://find?query=raspberry pi&subnet=192.168.1.0/24
        network://identify?ip=192.168.1.100
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "scan"
        
        self.subnet = uri.get_param("subnet") or self._detect_subnet()
        self.query = uri.get_param("query")  # For LLM queries
        self.ip = uri.get_param("ip")
        self.mac = uri.get_param("mac")
        self.timeout = int(uri.get_param("timeout", "10"))
        self.deep_scan = uri.get_param("deep", "false").lower() == "true"
        
    def process(self, data: Any) -> Dict:
        """Process network scan operation"""
        operations = {
            "scan": self._scan_network,
            "find": self._find_devices,
            "identify": self._identify_device,
            "monitor": self._monitor_network,
            "ports": self._scan_ports,
        }
        
        if self.operation not in operations:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operations[self.operation](data)
    
    def _detect_subnet(self) -> str:
        """Auto-detect local subnet"""
        try:
            # Get default gateway
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                match = re.search(r'via (\d+\.\d+\.\d+\.)', result.stdout)
                if match:
                    return f"{match.group(1)}0/24"
            
            # Fallback: get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            parts = local_ip.rsplit('.', 1)
            return f"{parts[0]}.0/24"
            
        except Exception:
            return "192.168.1.0/24"
    
    def _scan_network(self, data: Any) -> Dict:
        """Scan network for all devices"""
        devices = []
        
        # Try multiple scan methods
        devices = self._scan_with_nmap() or self._scan_with_arp() or self._scan_with_ping()
        
        # Enrich device info - first pass
        for device in devices:
            device["type"] = self._identify_device_type(device)
            device["description"] = DEVICE_SIGNATURES.get(device["type"], {}).get("description", "Unknown Device")
        
        # Second pass: scan ports for unknown devices to identify them
        for device in devices:
            if device["type"] == "unknown":
                ports = self._scan_common_ports(device["ip"])
                device["open_ports"] = ports
                device["services"] = self._identify_services(ports)
                
                # Re-identify based on ports
                new_type = self._identify_by_ports(ports)
                if new_type != "unknown":
                    device["type"] = new_type
                    device["description"] = DEVICE_SIGNATURES.get(new_type, {}).get("description", "Unknown Device")
        
        # Third pass: add connection info (RTSP URLs, print URLs, etc.)
        for device in devices:
            conn_info = self._get_connection_info(device)
            if conn_info:
                device["connection"] = conn_info
        
        # Group by type
        by_type = {}
        for device in devices:
            t = device["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(device)
        
        return {
            "success": True,
            "subnet": self.subnet,
            "total_devices": len(devices),
            "devices": devices,
            "by_type": by_type,
            "scan_method": "nmap" if self._has_nmap() else "arp"
        }
    
    def _identify_by_ports(self, ports: List[int]) -> str:
        """Identify device type based on open ports"""
        if not ports:
            return "unknown"
        
        port_set = set(ports)
        
        # Check port signatures
        if 554 in port_set:
            return "camera"
        if 9100 in port_set or 631 in port_set:
            return "printer"
        if 53 in port_set:
            return "router"
        if 5000 in port_set and 445 in port_set:
            return "nas"
        if 445 in port_set or 139 in port_set:
            return "nas"
        if 8008 in port_set or 8009 in port_set:
            return "smart_tv"
        if 8888 in port_set or 6006 in port_set:
            return "gpu_server"
        if 3306 in port_set or 5432 in port_set or 6379 in port_set or 27017 in port_set:
            return "server"
        if 3389 in port_set or 5900 in port_set:
            return "workstation"
        if 22 in port_set and len(port_set) == 1:
            return "raspberry_pi"
        if 22 in port_set and (80 in port_set or 443 in port_set):
            return "server"
        if 80 in port_set and len(port_set) <= 2:
            return "iot_device"
        
        return "unknown"
    
    def _scan_with_nmap(self) -> Optional[List[Dict]]:
        """Scan using nmap (most accurate)"""
        if not self._has_nmap():
            return None
        
        try:
            cmd = ["nmap", "-sn", self.subnet, "-oG", "-"]
            if self.deep_scan:
                cmd = ["nmap", "-sV", "-O", self.subnet, "-oG", "-"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                return None
            
            devices = []
            for line in result.stdout.split('\n'):
                if 'Host:' in line and 'Status: Up' in line:
                    match = re.search(r'Host: (\d+\.\d+\.\d+\.\d+) \(([^)]*)\)', line)
                    if match:
                        ip = match.group(1)
                        hostname = match.group(2) or ""
                        
                        mac = self._get_mac_for_ip(ip)
                        
                        devices.append({
                            "ip": ip,
                            "hostname": hostname,
                            "mac": mac,
                            "vendor": self._get_vendor(mac),
                            "status": "up"
                        })
            
            return devices if devices else None
            
        except Exception as e:
            logger.debug(f"nmap scan failed: {e}")
            return None
    
    def _scan_with_arp(self) -> Optional[List[Dict]]:
        """Scan using arp-scan"""
        try:
            result = subprocess.run(
                ["arp-scan", "--localnet", "-q"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                # Try with sudo
                result = subprocess.run(
                    ["sudo", "arp-scan", "--localnet", "-q"],
                    capture_output=True, text=True, timeout=60
                )
            
            devices = []
            for line in result.stdout.split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    ip = parts[0].strip()
                    mac = parts[1].strip() if len(parts) > 1 else ""
                    vendor = parts[2].strip() if len(parts) > 2 else ""
                    
                    if re.match(r'\d+\.\d+\.\d+\.\d+', ip):
                        hostname = self._resolve_hostname(ip)
                        devices.append({
                            "ip": ip,
                            "hostname": hostname,
                            "mac": mac.upper(),
                            "vendor": vendor or self._get_vendor(mac),
                            "status": "up"
                        })
            
            return devices if devices else None
            
        except Exception as e:
            logger.debug(f"arp-scan failed: {e}")
            return None
    
    def _scan_with_ping(self) -> List[Dict]:
        """Fallback: ping sweep"""
        devices = []
        base = self.subnet.rsplit('.', 1)[0]
        
        # Quick ping sweep
        for i in range(1, 255):
            ip = f"{base}.{i}"
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", ip],
                    capture_output=True, timeout=2
                )
                
                if result.returncode == 0:
                    mac = self._get_mac_for_ip(ip)
                    hostname = self._resolve_hostname(ip)
                    
                    devices.append({
                        "ip": ip,
                        "hostname": hostname,
                        "mac": mac,
                        "vendor": self._get_vendor(mac),
                        "status": "up"
                    })
            except Exception:
                continue
        
        return devices
    
    def _find_devices(self, data: Any) -> Dict:
        """Find devices by type using LLM to interpret query"""
        if not self.query:
            raise ComponentError("Query required for find operation")
        
        # First, scan the network
        scan_result = self._scan_network(data)
        devices = scan_result.get("devices", [])
        
        # Use LLM to interpret query and filter devices
        filtered = self._llm_filter_devices(devices, self.query)
        
        # Group by type for output
        by_type = {}
        for device in filtered:
            t = device.get("type", "unknown")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(device)
        
        return {
            "success": True,
            "query": self.query,
            "subnet": self.subnet,
            "matched_devices": len(filtered),
            "total_scanned": len(devices),
            "devices": filtered,
            "by_type": by_type
        }
    
    def _llm_filter_devices(self, devices: List[Dict], query: str) -> List[Dict]:
        """Use LLM to filter devices based on natural language query"""
        
        # First try rule-based matching
        query_lower = query.lower()
        
        # Map common queries to device types
        type_mappings = {
            "raspberry": "raspberry_pi",
            "rpi": "raspberry_pi",
            "pi": "raspberry_pi",
            "camera": "camera",
            "cam": "camera",
            "ipcam": "camera",
            "security": "camera",
            "printer": "printer",
            "drukark": "printer",  # Polish
            "router": "router",
            "access point": "router",
            "ap": "router",
            "nas": "nas",
            "storage": "nas",
            "tv": "smart_tv",
            "telewiz": "smart_tv",  # Polish
            "media": "smart_tv",
            "iot": "iot_device",
            "smart": "iot_device",
            "esp": "iot_device",
            "server": "server",
            "serwer": "server",  # Polish
        }
        
        # Check for direct type match
        matched_type = None
        for keyword, device_type in type_mappings.items():
            if keyword in query_lower:
                matched_type = device_type
                break
        
        if matched_type:
            return [d for d in devices if d.get("type") == matched_type]
        
        # Use LLM for complex queries
        try:
            import requests
            
            devices_json = json.dumps([{
                "ip": d["ip"],
                "hostname": d.get("hostname", ""),
                "mac": d.get("mac", ""),
                "vendor": d.get("vendor", ""),
                "type": d.get("type", "unknown"),
                "description": d.get("description", "")
            } for d in devices], indent=2)
            
            prompt = f"""Given this list of network devices:

{devices_json}

User query: "{query}"

Return ONLY a JSON array of IP addresses that match the query.
Example: ["192.168.1.10", "192.168.1.20"]

If no devices match, return: []
"""
            
            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            model = config.get("SQ_MODEL", "qwen2.5:14b")
            timeout = int(config.get("SQ_LLM_TIMEOUT", "30"))
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=timeout
            )
            
            if response.ok:
                result_text = response.json().get("response", "[]")
                # Extract JSON array from response
                match = re.search(r'\[.*?\]', result_text, re.DOTALL)
                if match:
                    matched_ips = json.loads(match.group())
                    return [d for d in devices if d["ip"] in matched_ips]
                    
        except Exception as e:
            logger.debug(f"LLM filter failed: {e}")
        
        # Fallback: simple text matching
        return [d for d in devices if 
                query_lower in d.get("hostname", "").lower() or
                query_lower in d.get("vendor", "").lower() or
                query_lower in d.get("description", "").lower()]
    
    def _identify_device(self, data: Any) -> Dict:
        """Identify a single device"""
        if not self.ip and not self.mac:
            raise ComponentError("IP or MAC address required")
        
        device = {
            "ip": self.ip,
            "mac": self.mac or self._get_mac_for_ip(self.ip),
            "hostname": self._resolve_hostname(self.ip) if self.ip else "",
            "vendor": "",
            "open_ports": [],
            "services": []
        }
        
        device["vendor"] = self._get_vendor(device["mac"])
        device["type"] = self._identify_device_type(device)
        device["description"] = DEVICE_SIGNATURES.get(device["type"], {}).get("description", "Unknown")
        
        # Scan common ports
        if self.ip:
            device["open_ports"] = self._scan_common_ports(self.ip)
            device["services"] = self._identify_services(device["open_ports"])
        
        return {
            "success": True,
            "device": device
        }
    
    def _monitor_network(self, data: Any) -> Dict:
        """Monitor network for changes (returns current state for comparison)"""
        scan_result = self._scan_network(data)
        
        return {
            "success": True,
            "subnet": self.subnet,
            "snapshot_time": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            "devices": scan_result.get("devices", []),
            "device_count": scan_result.get("total_devices", 0)
        }
    
    def _scan_ports(self, data: Any) -> Dict:
        """Scan ports on specific IP"""
        if not self.ip:
            raise ComponentError("IP address required for port scan")
        
        open_ports = self._scan_common_ports(self.ip)
        services = self._identify_services(open_ports)
        
        return {
            "success": True,
            "ip": self.ip,
            "open_ports": open_ports,
            "services": services
        }
    
    def _identify_device_type(self, device: Dict) -> str:
        """Identify device type based on MAC, hostname, ports"""
        mac = device.get("mac", "").upper()
        hostname = device.get("hostname", "").lower()
        ports = device.get("open_ports", [])
        
        # First check MAC_VENDORS database (most accurate)
        mac_type = self._get_type_from_mac(mac)
        if mac_type:
            return mac_type
        
        # Then check DEVICE_SIGNATURES
        for device_type, signatures in DEVICE_SIGNATURES.items():
            # Check MAC prefix
            for prefix in signatures.get("mac_prefixes", []):
                if mac.startswith(prefix.upper()):
                    return device_type
            
            # Check hostname
            for name_pattern in signatures.get("hostnames", []):
                if name_pattern in hostname:
                    return device_type
            
            # Check ports (if we have port info)
            if ports:
                sig_ports = signatures.get("ports", [])
                if any(p in ports for p in sig_ports):
                    return device_type
        
        return "unknown"
    
    def _get_mac_for_ip(self, ip: str) -> str:
        """Get MAC address for IP from ARP table"""
        try:
            result = subprocess.run(
                ["arp", "-n", ip],
                capture_output=True, text=True, timeout=5
            )
            
            match = re.search(r'([0-9A-Fa-f:]{17})', result.stdout)
            if match:
                return match.group(1).upper()
        except Exception:
            pass
        return ""
    
    def _resolve_hostname(self, ip: str) -> str:
        """Resolve hostname for IP"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except Exception:
            return ""
    
    def _get_vendor(self, mac: str) -> str:
        """Get vendor from MAC address using MAC_VENDORS database"""
        if not mac:
            return ""
        
        prefix = mac[:8].upper()
        vendor_info = MAC_VENDORS.get(prefix, {})
        return vendor_info.get("vendor", "")
    
    def _get_type_from_mac(self, mac: str) -> Optional[str]:
        """Get device type from MAC address"""
        if not mac:
            return None
        
        prefix = mac[:8].upper()
        vendor_info = MAC_VENDORS.get(prefix, {})
        return vendor_info.get("type")
    
    def _get_connection_info(self, device: Dict) -> Dict:
        """Get connection info (RTSP paths, print URLs, etc.) for device"""
        vendor = device.get("vendor", "")
        ip = device.get("ip", "")
        device_type = device.get("type", "")
        
        info = VENDOR_CONNECTION_INFO.get(vendor, {})
        if not info:
            return {}
        
        result = {"vendor": vendor}
        
        # Format RTSP paths for cameras
        if "rtsp_paths" in info:
            default_user = info.get("default_user", "admin")
            default_pass = info.get("default_pass", "admin")
            
            result["rtsp"] = []
            for path in info["rtsp_paths"]:
                formatted = path.format(
                    ip=ip,
                    user=default_user,
                    **{"pass": default_pass}  # 'pass' is keyword
                )
                result["rtsp"].append(formatted)
            
            result["default_credentials"] = f"{default_user}/{default_pass}"
        
        # Format print URLs for printers
        if "print_url" in info:
            result["print_url"] = info["print_url"].format(ip=ip)
        if "ipp_url" in info:
            result["ipp_url"] = info["ipp_url"].format(ip=ip)
        
        # Web UI
        if "web_port" in info:
            result["web_ui"] = f"http://{ip}:{info['web_port']}"
        if "https_port" in info:
            result["web_ui_https"] = f"https://{ip}:{info['https_port']}"
        
        # Notes
        if "notes" in info:
            result["notes"] = info["notes"].format(ip=ip)
        
        return result
    
    def _scan_common_ports(self, ip: str) -> List[int]:
        """Quick scan of common ports"""
        common_ports = [22, 23, 80, 443, 445, 554, 631, 3306, 5000, 5432, 8080, 8443, 9100]
        open_ports = []
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
            except Exception:
                continue
        
        return open_ports
    
    def _identify_services(self, ports: List[int]) -> List[Dict]:
        """Identify services from open ports"""
        services_map = {
            22: {"name": "SSH", "description": "Secure Shell"},
            23: {"name": "Telnet", "description": "Telnet"},
            80: {"name": "HTTP", "description": "Web Server"},
            443: {"name": "HTTPS", "description": "Secure Web Server"},
            445: {"name": "SMB", "description": "File Sharing"},
            554: {"name": "RTSP", "description": "Streaming (Camera)"},
            631: {"name": "IPP", "description": "Printing"},
            3306: {"name": "MySQL", "description": "MySQL Database"},
            5000: {"name": "Synology", "description": "NAS Web UI"},
            5432: {"name": "PostgreSQL", "description": "PostgreSQL Database"},
            8080: {"name": "HTTP-Alt", "description": "Alternative Web Server"},
            8443: {"name": "HTTPS-Alt", "description": "Alternative HTTPS"},
            9100: {"name": "JetDirect", "description": "Printer"},
        }
        
        return [
            {"port": p, **services_map.get(p, {"name": "Unknown", "description": "Unknown service"})}
            for p in ports
        ]
    
    def _has_nmap(self) -> bool:
        """Check if nmap is installed"""
        try:
            subprocess.run(["nmap", "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False


# Quick helper functions
def scan_network(subnet: str = None) -> Dict:
    """Quick network scan"""
    from ..core import flow
    uri = f"network://scan"
    if subnet:
        uri += f"?subnet={subnet}"
    return flow(uri).run()


def find_devices(query: str, subnet: str = None) -> Dict:
    """Find devices by query"""
    from ..core import flow
    uri = f"network://find?query={query}"
    if subnet:
        uri += f"&subnet={subnet}"
    return flow(uri).run()


def find_cameras(subnet: str = None) -> Dict:
    """Find all cameras on network"""
    return find_devices("cameras", subnet)


def find_raspberry_pi(subnet: str = None) -> Dict:
    """Find all Raspberry Pi devices"""
    return find_devices("raspberry pi", subnet)


def find_printers(subnet: str = None) -> Dict:
    """Find all printers"""
    return find_devices("printers", subnet)
