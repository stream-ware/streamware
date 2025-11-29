# Streamware Bash Scripts

Ready-to-use bash scripts for common security and monitoring tasks.

## ⚙️ Setup

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit with your settings
nano .env

# 3. Make scripts executable
chmod +x *.sh
```

## 📁 Scripts

### Core Scripts
| Script | Description |
|--------|-------------|
| `common.sh` | **Shared functions** - source this in your scripts |
| `.env.example` | **Configuration template** - copy to .env |

### Discovery & Setup
| Script | Description |
|--------|-------------|
| `01_camera_discovery.sh` | Find all cameras on network |
| `07_setup_config.sh` | Setup configuration and .env |
| `08_network_scan.sh` | Scan network for all devices |

### Stream Analysis
| Script | Description |
|--------|-------------|
| `02_stream_analysis.sh` | Analyze camera stream for activity |
| `03_generate_report.sh` | Generate HTML report with images |
| `05_people_counting.sh` | Count people over time |

### Monitoring
| Script | Description |
|--------|-------------|
| `06_motion_alert.sh` | Continuous monitoring with alerts |
| `12_continuous_monitor.sh` | **24/7 monitoring** with rate limiting |
| `13_multi_camera.sh` | **Monitor all cameras** at once |

### Use Cases
| Script | Description |
|--------|-------------|
| `10_parking_monitor.sh` | 🚗 Monitor parking lot for vehicles |
| `11_entrance_monitor.sh` | 🚪 Monitor entrance with zone detection |
| `15_package_detection.sh` | 📦 Detect package deliveries |
| `16_pet_monitor.sh` | 🐾 Monitor pets at home |

### Pipelines & Reports
| Script | Description |
|--------|-------------|
| `04_full_security_pipeline.sh` | Complete pipeline: discover → analyze → alert |
| `09_complete_workflow.sh` | Interactive end-to-end demo |
| `14_daily_report.sh` | Generate daily activity summary |

## 🚀 Quick Start

```bash
# Make scripts executable
chmod +x *.sh

# Run discovery
./01_camera_discovery.sh

# Analyze camera (pass RTSP URL as argument)
./02_stream_analysis.sh "rtsp://admin:pass@192.168.1.100:554/stream"

# Generate report
./03_generate_report.sh "rtsp://admin:pass@192.168.1.100:554/stream" 60 ./reports

# Full pipeline (auto-discovers cameras)
./04_full_security_pipeline.sh

# Complete interactive demo
./09_complete_workflow.sh
```

## 📋 Usage Examples

### Find Cameras
```bash
./01_camera_discovery.sh

# Or directly with sq:
sq network find "cameras" --yaml
```

### Analyze with Custom Settings
```bash
./02_stream_analysis.sh "rtsp://camera/live" 60 person

# Arguments:
#   $1 = RTSP URL
#   $2 = Duration (seconds)
#   $3 = Focus (person, vehicle, animal)
```

### Generate Report
```bash
./03_generate_report.sh "rtsp://camera/live" 120 ~/reports

# Arguments:
#   $1 = RTSP URL
#   $2 = Duration (seconds)
#   $3 = Output directory
```

### Continuous Monitoring with Alerts
```bash
# Set environment variables for alerts
export SLACK_WEBHOOK="https://hooks.slack.com/services/xxx"
export TELEGRAM_TOKEN="your_bot_token"
export TELEGRAM_CHAT="your_chat_id"

# Run monitoring
./06_motion_alert.sh "rtsp://camera/live" 60
```

## ⚙️ Configuration

### Setup .env
```bash
./07_setup_config.sh

# Or manually:
sq config --init
sq config --set SQ_MODEL llava:13b --save
sq config --set SQ_STREAM_FOCUS person --save
```

### Web Configuration
```bash
sq config --web
# Open: http://localhost:8080
```

## 🔧 Requirements

- `streamware` installed (`pip install streamware`)
- `ollama` with `llava:13b` model
- `ffmpeg` for video processing
- `jq` for JSON processing (optional but recommended)

### Install jq
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Or run without jq (some features won't work)
```

## 📝 .env Configuration

All scripts use `.env` for configuration. Copy `.env.example` and customize:

```bash
# Camera Settings
CAMERA_URL="rtsp://admin:password@192.168.1.100:554/stream"
CAMERA_USER="admin"
CAMERA_PASS="password"

# Analysis Settings
DURATION=60
INTERVAL=10
FOCUS="person"
SENSITIVITY="low"

# Slack Alerts
SLACK_WEBHOOK="https://hooks.slack.com/services/xxx"

# Telegram Alerts
TELEGRAM_TOKEN="your_bot_token"
TELEGRAM_CHAT="your_chat_id"

# Output
REPORTS_DIR="./reports"
LOGS_DIR="./logs"
```

### Using common.sh

Source `common.sh` in your scripts to use shared functions:

```bash
#!/bin/bash
source "$(dirname "$0")/common.sh"

# Now you have:
# - All .env variables loaded
# - print_header, print_success, print_error functions
# - send_alert (Slack + Telegram)
# - log_message
# - get_first_camera, get_all_cameras
# - ensure_camera_url

print_header "My Custom Monitor"
ensure_camera_url
show_config

# Your monitoring logic here...

send_alert "Motion detected!"
```

## 🕐 Cron Examples

```bash
# Check cameras every 5 minutes
*/5 * * * * cd /path/to/scripts && ./13_multi_camera.sh >> logs/cron.log 2>&1

# Daily report at midnight
0 0 * * * cd /path/to/scripts && ./14_daily_report.sh

# Package detection during delivery hours
*/15 8-18 * * * cd /path/to/scripts && ./15_package_detection.sh

# 24/7 monitoring (run in screen/tmux)
./12_continuous_monitor.sh
```

## 📚 Related

- [QUICKSTART.md](../QUICKSTART.md) - Quick start guide
- [network/README.md](../network/README.md) - Network scanning examples
- [media-processing/README.md](../media-processing/README.md) - Media processing examples
