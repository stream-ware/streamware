#!/bin/bash
# =============================================================================
# Email Alerts - Person detection with email notification
# Sends email when person is detected
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "📧 Email Alerts - Person Detection"

CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

print_step "Configuration check..."

# Check email settings
if [[ -z "$SMTP_USER" || -z "$SMTP_PASS" || -z "$EMAIL_TO" ]]; then
    print_warning "Email not configured!"
    echo ""
    echo "Add to your .env file:"
    echo "  SMTP_HOST=smtp.gmail.com"
    echo "  SMTP_PORT=587"
    echo "  SMTP_USER=your-email@gmail.com"
    echo "  SMTP_PASS=your-app-password"
    echo "  EMAIL_TO=recipient@example.com"
    echo ""
    echo "For Gmail, create an App Password:"
    echo "  https://myaccount.google.com/apppasswords"
    echo ""
fi

print_step "Watching for person (will email on detection)..."
echo "Camera: $CAMERA_URL"
echo "Duration: ${DURATION:-120}s"
echo ""

# Export for Python
export SQ_SMTP_SERVER="${SMTP_HOST:-smtp.gmail.com}"
export SQ_SMTP_PORT="${SMTP_PORT:-587}"
export SQ_SMTP_USER="$SMTP_USER"
export SQ_SMTP_PASSWORD="$SMTP_PASS"
export SQ_EMAIL_FROM="${EMAIL_FROM:-$SMTP_USER}"
export SQ_EMAIL_TO="$EMAIL_TO"

# Use Python for email alert integration
python3 << 'PYEOF'
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamware.components import watch_for
from streamware.helpers import send_alert

camera_url = os.environ.get("CAMERA_URL")
duration = int(os.environ.get("DURATION", "120"))

print("👁️ Watching for person...")
print()

result = watch_for(
    camera_url,
    conditions=["person appears", "person visible", "someone enters"],
    duration=duration,
    tts=False
)

alerts = result.get("alerts", [])
if alerts:
    print(f"🔴 {len(alerts)} person detection(s)!")
    
    # Send email
    message = f"Person detected on camera!\n\nAlerts:\n"
    for alert in alerts:
        message += f"- {alert.get('timestamp')}: {alert.get('description', '')[:100]}\n"
    
    result = send_alert(message, email=True)
    
    if "email" in result.get("sent_to", []):
        print("📧 Email sent successfully!")
    else:
        print(f"❌ Email failed: {result.get('email_error', 'unknown')}")
else:
    print("✅ No person detected")

PYEOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 More Alert Options:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Python: Send to multiple channels"
echo "from streamware.helpers import send_alert"
echo "send_alert('Person detected!', email=True, slack=True, telegram=True)"
echo ""
echo "# CLI with watch command"
echo "sq watch --url \"\$URL\" --detect person --alert slack"
echo ""
