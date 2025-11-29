"""
Streamware Helpers - Simplified API for common tasks

One-liner functions for the most common use cases.
Import and use directly without building URIs.

Usage:
    from streamware.helpers import *
    
    # Network
    cameras = find_cameras()
    devices = scan_network()
    
    # Stream Analysis  
    result = watch_camera("rtsp://camera/live", focus="person")
    
    # Tracking
    people = count_people("rtsp://camera/live")
    
    # Alerts
    send_alert("Motion detected!", slack=True, email=True)
"""

from typing import Dict, List, Optional, Any
from pathlib import Path

# ============================================================================
# Network Discovery
# ============================================================================

def scan_network(subnet: str = None, timeout: int = 10) -> Dict:
    """
    Scan network for all devices.
    
    Returns:
        Dict with devices grouped by type (cameras, printers, etc.)
    
    Example:
        result = scan_network()
        for camera in result['by_type'].get('camera', []):
            print(f"Camera: {camera['ip']} - {camera['vendor']}")
    """
    from .components.network_scan import scan_network as _scan
    return _scan(subnet=subnet, timeout=timeout)


def find_cameras(subnet: str = None) -> List[Dict]:
    """
    Find all cameras on network with RTSP URLs.
    
    Returns:
        List of camera dicts with IP, vendor, RTSP URLs
    
    Example:
        cameras = find_cameras()
        for cam in cameras:
            print(f"{cam['ip']}: {cam.get('connection', {}).get('rtsp', ['N/A'])[0]}")
    """
    from .components.network_scan import find_cameras as _find
    result = _find(subnet=subnet)
    return result.get("devices", [])


def find_printers(subnet: str = None) -> List[Dict]:
    """
    Find all printers on network.
    
    Returns:
        List of printer dicts with IP, vendor, print URLs
    """
    from .components.network_scan import find_printers as _find
    result = _find(subnet=subnet)
    return result.get("devices", [])


def find_devices(query: str, subnet: str = None) -> List[Dict]:
    """
    Find devices by natural language query.
    
    Example:
        servers = find_devices("GPU servers")
        nas = find_devices("storage devices")
    """
    from .components.network_scan import find_devices as _find
    result = _find(query=query, subnet=subnet)
    return result.get("devices", [])


def get_device_info(ip: str) -> Dict:
    """
    Get detailed info about a specific device.
    
    Example:
        info = get_device_info("192.168.1.100")
        print(f"Type: {info['type']}, Vendor: {info['vendor']}")
    """
    from .components.network_scan import identify_device
    return identify_device(ip=ip)


# ============================================================================
# Camera & Stream Analysis
# ============================================================================

def watch_camera(url: str, focus: str = None, duration: int = 30, 
                 interval: int = 5, sensitivity: str = "medium") -> Dict:
    """
    Watch camera stream and detect changes.
    
    Args:
        url: RTSP URL of camera
        focus: What to focus on (person, vehicle, animal, motion)
        duration: How long to watch (seconds)
        interval: Seconds between frames
        sensitivity: low/medium/high
    
    Returns:
        Dict with timeline, changes, summary
    
    Example:
        result = watch_camera(
            "rtsp://admin:pass@192.168.1.100:554/stream",
            focus="person",
            duration=60
        )
        if result['significant_changes'] > 0:
            print("Activity detected!")
    """
    from .core import flow
    
    uri = f"stream://rtsp?url={url}&mode=diff&duration={duration}&interval={interval}&sensitivity={sensitivity}"
    if focus:
        uri += f"&focus={focus}"
    
    return flow(uri).run()


def analyze_stream(url: str, mode: str = "diff", duration: int = 30) -> Dict:
    """
    Analyze any video stream.
    
    Args:
        url: Stream URL (rtsp://, http://, file path)
        mode: full, stream, or diff
        duration: Analysis duration
    
    Example:
        result = analyze_stream("rtsp://camera/live", "diff", 60)
    """
    from .core import flow
    return flow(f"stream://rtsp?url={url}&mode={mode}&duration={duration}").run()


def capture_screen(mode: str = "diff", duration: int = 30, interval: int = 5) -> Dict:
    """
    Analyze screen for changes.
    
    Example:
        result = capture_screen("diff", 60, 10)
    """
    from .core import flow
    return flow(f"stream://screen?mode={mode}&duration={duration}&interval={interval}").run()


def watch_webcam(mode: str = "stream", duration: int = 30, device: str = "0") -> Dict:
    """
    Analyze webcam stream.
    
    Example:
        result = watch_webcam("stream", 60)
    """
    from .core import flow
    return flow(f"stream://webcam?mode={mode}&duration={duration}&device={device}").run()


# ============================================================================
# Object Tracking
# ============================================================================

def count_people(source: str, duration: int = 60, interval: int = 5) -> Dict:
    """
    Count people over time.
    
    Example:
        result = count_people("rtsp://camera/live", 300)
        stats = result['statistics']['person']
        print(f"People: min={stats['min']}, max={stats['max']}, avg={stats['avg']:.1f}")
    """
    from .components.tracking import count_people as _count
    return _count(source, duration, interval)


def track_person(source: str, name: str = None, duration: int = 60) -> Dict:
    """
    Track person movement.
    
    Example:
        result = track_person("rtsp://camera/live", "Visitor", 120)
        trajectory = result['trajectory']
    """
    from .components.tracking import track_person as _track
    return _track(source, name, duration)


def detect_objects(source: str, objects: str = "person,vehicle", 
                   duration: int = 30) -> Dict:
    """
    Detect objects in video.
    
    Example:
        result = detect_objects("rtsp://camera/live", "person,vehicle,animal")
    """
    from .components.tracking import detect_objects as _detect
    return _detect(source, objects, duration)


def detect_vehicles(source: str, duration: int = 60) -> Dict:
    """
    Detect vehicles in video.
    
    Example:
        result = detect_vehicles("rtsp://parking/camera", 300)
    """
    from .components.tracking import detect_vehicles as _detect
    return _detect(source, duration)


def monitor_zone(source: str, zone_name: str, x: int, y: int, 
                 w: int, h: int, duration: int = 60) -> Dict:
    """
    Monitor zone for entry/exit.
    
    Example:
        result = monitor_zone("rtsp://camera/live", "entrance", 0, 0, 200, 300, 600)
        for event in result['events']:
            print(f"{event['type']}: {event['object_type']}")
    """
    from .components.tracking import monitor_zone as _monitor
    return _monitor(source, zone_name, x, y, w, h, duration)


# ============================================================================
# Alerts & Notifications
# ============================================================================

def send_alert(message: str, slack: bool = False, email: bool = False,
               telegram: bool = False, webhook: str = None) -> Dict:
    """
    Send alert notification.
    
    Args:
        message: Alert message
        slack: Send to Slack (uses SQ_SLACK_WEBHOOK from .env)
        email: Send email (uses SQ_EMAIL_* from .env)
        telegram: Send to Telegram (uses SQ_TELEGRAM_* from .env)
        webhook: Custom webhook URL
    
    Example:
        send_alert("Motion detected on front camera!", slack=True)
    """
    from .config import config
    results = {"message": message, "sent_to": []}
    
    if slack:
        webhook_url = config.get("SQ_SLACK_WEBHOOK")
        if webhook_url:
            try:
                import requests
                requests.post(webhook_url, json={"text": message}, timeout=5)
                results["sent_to"].append("slack")
            except Exception as e:
                results["slack_error"] = str(e)
    
    if telegram:
        token = config.get("SQ_TELEGRAM_BOT_TOKEN")
        chat_id = config.get("SQ_TELEGRAM_CHAT_ID")
        if token and chat_id:
            try:
                import requests
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
                results["sent_to"].append("telegram")
            except Exception as e:
                results["telegram_error"] = str(e)
    
    if email:
        smtp_server = config.get("SQ_SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(config.get("SQ_SMTP_PORT", "587"))
        smtp_user = config.get("SQ_SMTP_USER", config.get("SQ_EMAIL_FROM"))
        smtp_pass = config.get("SQ_SMTP_PASSWORD")
        email_to = config.get("SQ_EMAIL_TO")
        email_from = config.get("SQ_EMAIL_FROM", smtp_user)
        
        if smtp_user and smtp_pass and email_to:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                msg = MIMEMultipart()
                msg['From'] = email_from
                msg['To'] = email_to
                msg['Subject'] = f"🚨 Streamware Alert: {message[:50]}"
                
                body = f"""
Streamware Alert
================

{message}

---
Sent by Streamware monitoring system
"""
                msg.attach(MIMEText(body, 'plain'))
                
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                
                results["sent_to"].append("email")
            except Exception as e:
                results["email_error"] = str(e)
        else:
            results["email_error"] = "Missing SQ_SMTP_* or SQ_EMAIL_* config"
    
    if webhook:
        try:
            import requests
            requests.post(webhook, json={"message": message}, timeout=5)
            results["sent_to"].append("webhook")
        except Exception as e:
            results["webhook_error"] = str(e)
    
    return results


def log_event(event_type: str, data: Dict, file: str = "events.jsonl") -> None:
    """
    Log event to file.
    
    Example:
        log_event("motion_detected", {"camera": "front", "objects": 2})
    """
    import json
    from datetime import datetime
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        **data
    }
    
    with open(file, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ============================================================================
# Reports
# ============================================================================

def generate_report(result: Dict, output: str, title: str = "Analysis Report") -> str:
    """
    Generate HTML report from analysis result.
    
    Args:
        result: Analysis result dict
        output: Output file path (.html)
        title: Report title
    
    Returns:
        Path to generated report
    
    Example:
        result = watch_camera("rtsp://camera/live", focus="person", duration=60)
        generate_report(result, "security_report.html", "Security Analysis")
    """
    from datetime import datetime
    
    timeline = result.get("timeline", result.get("detections", []))
    changes = result.get("significant_changes", len([t for t in timeline if t.get("type") == "change"]))
    
    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>{title}</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white p-8">
<div class="max-w-4xl mx-auto">
<h1 class="text-3xl font-bold mb-4">{title}</h1>
<p class="text-gray-400 mb-8">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div class="grid grid-cols-3 gap-4 mb-8">
<div class="bg-gray-800 p-4 rounded"><div class="text-2xl font-bold">{len(timeline)}</div><div class="text-gray-400">Frames</div></div>
<div class="bg-gray-800 p-4 rounded"><div class="text-2xl font-bold {'text-red-400' if changes > 0 else 'text-green-400'}">{changes}</div><div class="text-gray-400">Changes</div></div>
<div class="bg-gray-800 p-4 rounded"><div class="text-lg">{'🔴 ACTIVITY' if changes > 0 else '✅ STABLE'}</div><div class="text-gray-400">Status</div></div>
</div>

<h2 class="text-xl font-bold mb-4">Timeline</h2>
<div class="space-y-4">
"""
    
    for event in timeline[:50]:  # Limit to 50
        is_change = event.get("type") == "change"
        border = "border-red-500" if is_change else "border-gray-700"
        status = "🔴 CHANGE" if is_change else "⚪ stable"
        
        html += f"""<div class="border {border} rounded p-4">
<div class="flex justify-between mb-2">
<span>Frame {event.get('frame', '?')}</span>
<span>{event.get('timestamp', '')}</span>
<span>{status}</span>
</div>
<div class="text-sm text-gray-300">{str(event.get('changes', event.get('description', '')))[:300]}</div>
</div>
"""
    
    html += """</div></div></body></html>"""
    
    with open(output, "w") as f:
        f.write(html)
    
    return output


# ============================================================================
# Quick Pipelines
# ============================================================================

def security_check(camera_url: str, duration: int = 30, 
                   alert_on_change: bool = False) -> Dict:
    """
    Quick security check on camera.
    
    Args:
        camera_url: RTSP URL
        duration: Check duration
        alert_on_change: Send alert if activity detected
    
    Returns:
        Dict with status, changes, summary
    
    Example:
        result = security_check("rtsp://admin:pass@camera/live", 60, alert_on_change=True)
        if result['activity']:
            print("Security alert!")
    """
    result = watch_camera(camera_url, focus="person,vehicle", duration=duration, sensitivity="low")
    
    activity = result.get("significant_changes", 0) > 0
    
    if activity and alert_on_change:
        send_alert(f"🚨 Activity detected on camera: {result.get('significant_changes')} changes", slack=True)
    
    return {
        "activity": activity,
        "changes": result.get("significant_changes", 0),
        "frames": result.get("frames_analyzed", 0),
        "timeline": result.get("timeline", []),
        "status": "ACTIVITY_DETECTED" if activity else "STABLE"
    }


def monitor_all_cameras(duration: int = 30, alert_on_change: bool = False) -> Dict:
    """
    Monitor all cameras on network.
    
    Example:
        results = monitor_all_cameras(60, alert_on_change=True)
        for ip, status in results['cameras'].items():
            print(f"{ip}: {status['status']}")
    """
    cameras = find_cameras()
    results = {"cameras": {}, "alerts": 0}
    
    for cam in cameras:
        ip = cam.get("ip")
        rtsp_urls = cam.get("connection", {}).get("rtsp", [])
        
        if rtsp_urls:
            try:
                check = security_check(rtsp_urls[0], duration, alert_on_change)
                results["cameras"][ip] = check
                if check["activity"]:
                    results["alerts"] += 1
            except Exception as e:
                results["cameras"][ip] = {"error": str(e)}
    
    return results


def occupancy_report(camera_url: str, duration: int = 300, interval: int = 30) -> Dict:
    """
    Generate occupancy report.
    
    Example:
        report = occupancy_report("rtsp://camera/live", 3600, 60)
        print(f"Average occupancy: {report['average']:.1f} people")
    """
    result = count_people(camera_url, duration, interval)
    stats = result.get("statistics", {}).get("person", {})
    
    return {
        "min": stats.get("min", 0),
        "max": stats.get("max", 0),
        "average": stats.get("avg", 0),
        "timeline": result.get("timeline", []),
        "duration_seconds": duration
    }
