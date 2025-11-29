#!/bin/bash
# =============================================================================
# Common Functions and Configuration Loader
# Source this file in your scripts: source ./common.sh
# =============================================================================

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env if exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
    ENV_LOADED=true
else
    ENV_LOADED=false
fi

# -----------------------------------------------------------------------------
# Default Values (if not set in .env)
# -----------------------------------------------------------------------------
CAMERA_URL="${CAMERA_URL:-}"
CAMERA_USER="${CAMERA_USER:-admin}"
CAMERA_PASS="${CAMERA_PASS:-admin}"
DURATION="${DURATION:-60}"
INTERVAL="${INTERVAL:-10}"
FOCUS="${FOCUS:-person}"
SENSITIVITY="${SENSITIVITY:-low}"
MODEL="${MODEL:-llava:13b}"
REPORTS_DIR="${REPORTS_DIR:-./reports}"
LOGS_DIR="${LOGS_DIR:-./logs}"
FRAMES_DIR="${FRAMES_DIR:-./frames}"
MONITOR_INTERVAL="${MONITOR_INTERVAL:-60}"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

# Print header
print_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo ""
}

# Print step
print_step() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Print info
print_info() {
    echo "ℹ️  $1"
}

# Print success
print_success() {
    echo "✅ $1"
}

# Print warning
print_warning() {
    echo "⚠️  $1"
}

# Print error
print_error() {
    echo "❌ $1"
}

# Create directories
setup_dirs() {
    mkdir -p "$REPORTS_DIR" "$LOGS_DIR" "$FRAMES_DIR"
}

# Get timestamp
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Get filename timestamp
get_file_timestamp() {
    date '+%Y%m%d_%H%M%S'
}

# Log message
log_message() {
    local level="$1"
    local message="$2"
    local log_file="${LOGS_DIR}/streamware.log"
    
    mkdir -p "$LOGS_DIR"
    echo "[$(get_timestamp)] [$level] $message" >> "$log_file"
}

# Send Slack alert
send_slack() {
    local message="$1"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\": \"$message\"}" > /dev/null
        return 0
    fi
    return 1
}

# Send Telegram alert
send_telegram() {
    local message="$1"
    if [ -n "$TELEGRAM_TOKEN" ] && [ -n "$TELEGRAM_CHAT" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT" \
            -d "text=$message" > /dev/null
        return 0
    fi
    return 1
}

# Send all configured alerts
send_alert() {
    local message="$1"
    local sent=false
    
    if send_slack "$message"; then
        print_info "Slack alert sent"
        sent=true
    fi
    
    if send_telegram "$message"; then
        print_info "Telegram alert sent"
        sent=true
    fi
    
    if [ "$sent" = false ]; then
        print_warning "No alert channels configured"
    fi
    
    log_message "ALERT" "$message"
}

# Get first camera from network
get_first_camera() {
    local cameras=$(sq network find "cameras" --json 2>/dev/null)
    echo "$cameras" | jq -r '.devices[0].connection.rtsp[0] // ""'
}

# Get all camera URLs
get_all_cameras() {
    local cameras=$(sq network find "cameras" --json 2>/dev/null)
    echo "$cameras" | jq -r '.devices[].connection.rtsp[0] // empty'
}

# Check if camera URL is set
ensure_camera_url() {
    if [ -z "$CAMERA_URL" ]; then
        print_warning "CAMERA_URL not set, discovering..."
        CAMERA_URL=$(get_first_camera)
        
        if [ -z "$CAMERA_URL" ]; then
            print_error "No camera found. Set CAMERA_URL in .env or pass as argument."
            exit 1
        fi
        
        print_success "Found camera: ${CAMERA_URL:0:50}..."
    fi
}

# Show configuration
show_config() {
    print_header "⚙️ Configuration"
    
    if [ "$ENV_LOADED" = true ]; then
        echo "📁 .env: Loaded from $SCRIPT_DIR/.env"
    else
        echo "📁 .env: Not found (using defaults)"
    fi
    echo ""
    echo "Camera URL: ${CAMERA_URL:0:50}..."
    echo "Duration: ${DURATION}s"
    echo "Interval: ${INTERVAL}s"
    echo "Focus: $FOCUS"
    echo "Sensitivity: $SENSITIVITY"
    echo "Reports: $REPORTS_DIR"
    echo ""
    
    if [ -n "$SLACK_WEBHOOK" ]; then
        echo "✅ Slack alerts: Enabled"
    else
        echo "⚪ Slack alerts: Not configured"
    fi
    
    if [ -n "$TELEGRAM_TOKEN" ]; then
        echo "✅ Telegram alerts: Enabled"
    else
        echo "⚪ Telegram alerts: Not configured"
    fi
    echo ""
}
