#!/bin/bash
# =============================================================================
# Setup Configuration
# Initialize and configure Streamware settings
# =============================================================================

echo "========================================"
echo "⚙️ Streamware Configuration Setup"
echo "========================================"
echo ""

# Check if .env exists
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    echo ""
    echo "Current configuration:"
    echo "----------------------"
    sq config --show | head -30
else
    echo "📝 Creating .env file..."
    sq config --init
fi

echo ""
echo "========================================"
echo "🔧 Recommended Settings"
echo "========================================"
echo ""

# Set recommended defaults
echo "Setting recommended values..."
echo ""

# AI Model
echo "# AI Model (llava:13b for better accuracy)"
sq config --set SQ_MODEL llava:13b --save
echo ""

# Detection settings
echo "# Detection focus (person by default)"
sq config --set SQ_STREAM_FOCUS person --save
echo ""

echo "# Sensitivity (low = fewer false alarms)"
sq config --set SQ_STREAM_SENSITIVITY low --save
echo ""

echo "# Reports directory"
sq config --set SQ_REPORTS_DIR ./reports --save
echo ""

echo "========================================"
echo "📋 Alert Configuration"
echo "========================================"
echo ""
echo "To enable Slack alerts, run:"
echo "  sq config --set SQ_SLACK_WEBHOOK 'https://hooks.slack.com/services/xxx' --save"
echo ""
echo "To enable Telegram alerts, run:"
echo "  sq config --set SQ_TELEGRAM_BOT_TOKEN 'your_bot_token' --save"
echo "  sq config --set SQ_TELEGRAM_CHAT_ID 'your_chat_id' --save"
echo ""
echo "To enable email alerts, run:"
echo "  sq config --set SQ_SMTP_HOST 'smtp.gmail.com' --save"
echo "  sq config --set SQ_SMTP_USER 'your_email@gmail.com' --save"
echo "  sq config --set SQ_SMTP_PASS 'your_app_password' --save"
echo "  sq config --set SQ_EMAIL_TO 'alerts@example.com' --save"
echo ""

echo "========================================"
echo "🌐 Web Configuration Panel"
echo "========================================"
echo ""
echo "For a visual configuration interface, run:"
echo "  sq config --web"
echo ""
echo "Then open: http://localhost:8080"
echo ""

echo "========================================"
echo "✅ Setup Complete"
echo "========================================"
echo ""
echo "View all settings:"
echo "  sq config --show"
echo ""
