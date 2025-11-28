# Streamware Communication Components Documentation

## Overview

Streamware provides comprehensive communication components for integrating with email, messaging platforms, and SMS services. These components enable you to build sophisticated multi-channel communication workflows for customer support, notifications, marketing automation, and more.

## Table of Contents

- [Installation](#installation)
- [Email Component](#email-component)
- [Telegram Component](#telegram-component)
- [WhatsApp Component](#whatsapp-component)
- [Discord Component](#discord-component)
- [Slack Component](#slack-component)
- [SMS Component](#sms-component)
- [Multi-Channel Examples](#multi-channel-examples)
- [Best Practices](#best-practices)

## Installation

Install Streamware with communication components:

```bash
pip install streamware[communication]

# Or install specific components
pip install streamware[telegram,slack,email]

# Install all components
pip install streamware[all]
```

## Email Component

### Configuration

```python
from streamware import flow

# Basic email sending
flow("email://send?to=user@example.com&subject=Hello").run("Message body")

# With SMTP configuration
flow("email://send"
     "?smtp_host=smtp.gmail.com"
     "&smtp_port=587"
     "&user=sender@gmail.com"
     "&password=app_password"
     "&to=recipient@example.com"
).run("Email content")
```

### Operations

| Operation | Description | URI Example |
|-----------|-------------|-------------|
| `send` | Send email | `email://send?to=user@example.com` |
| `read` | Read emails from inbox | `email://read?folder=INBOX&unread=true` |
| `watch` | Monitor inbox for new emails | `email-watch://interval=60` |
| `delete` | Delete email by ID | `email://delete` |
| `search` | Search emails | `email://search?criteria=UNSEEN` |

### Examples

```python
# Send HTML email with attachments
result = flow("email://send").with_data({
    "to": "user@example.com",
    "subject": "Monthly Report",
    "body": "Please find attached the monthly report.",
    "html": "<h1>Monthly Report</h1><p>See attachment</p>",
    "attachments": ["report.pdf", "data.xlsx"]
}).run()

# Watch inbox and process emails
for email in flow("email-watch://interval=30").stream():
    print(f"New email from {email['from']}: {email['subject']}")
    
# Filter and auto-respond
flow("email://read?unread=true") \
    | "email-filter://subject=Support" \
    | "transform://template?template=Thank you for contacting support..." \
    | "email://send"
```

## Telegram Component

### Configuration

```python
# Get bot token from @BotFather on Telegram
flow("telegram://send?chat_id=@channel&token=BOT_TOKEN").run("Message")
```

### Operations

| Operation | Description | URI Example |
|-----------|-------------|-------------|
| `send` | Send text message | `telegram://send?chat_id=123456` |
| `send_photo` | Send photo | `telegram://send_photo?chat_id=123456` |
| `send_document` | Send document | `telegram://send_document?chat_id=123456` |
| `poll` | Long polling for updates | `telegram://poll?timeout=30` |
| `webhook` | Set webhook | `telegram://webhook?url=https://myapp.com` |

### Bot Example

```python
# Create Telegram bot
bot_pipeline = (
    flow("telegram-bot://token=YOUR_BOT_TOKEN")
    | "telegram-command://"
    | "choose://"
      .when("$.command=='/start'", "telegram://send?text=Welcome!")
      .when("$.command=='/help'", "telegram://send?text=Available commands...")
      .otherwise("telegram://send?text=Unknown command")
)

# Process messages
for update in bot_pipeline.stream():
    print(f"Received: {update}")
```

## WhatsApp Component

### Providers

WhatsApp component supports multiple providers:

1. **WhatsApp Business API** (Official)
2. **Twilio WhatsApp**
3. **WhatsApp Web** (Automation)

### Configuration

```python
# Twilio WhatsApp
flow("whatsapp://send"
     "?provider=twilio"
     "&account_sid=YOUR_SID"
     "&auth_token=YOUR_TOKEN"
     "&from_number=+14155238886"  # Twilio WhatsApp number
).run({"phone": "+1234567890", "message": "Hello!"})

# WhatsApp Business API
flow("whatsapp://send"
     "?provider=business_api"
     "&token=YOUR_TOKEN"
     "&phone_number_id=YOUR_PHONE_ID"
).run({"phone": "+1234567890", "message": "Hello!"})
```

### Template Messages

```python
# Send template message
flow("whatsapp://template"
     "?template=order_confirmation"
     "&language=en"
).run({
    "phone": "+1234567890",
    "parameters": ["ORDER123", "$99.99", "2 days"]
})
```

## Discord Component

### Configuration

```python
# Discord bot token from Discord Developer Portal
flow("discord://send?channel_id=123456&token=BOT_TOKEN").run("Message")
```

### Operations

| Operation | Description | URI Example |
|-----------|-------------|-------------|
| `send` | Send message | `discord://send?channel_id=123456` |
| `send_embed` | Send embedded message | `discord://send_embed?channel_id=123456` |
| `webhook` | Send via webhook | `discord://webhook?url=WEBHOOK_URL` |
| `create_thread` | Create thread | `discord://create_thread?channel_id=123456` |

### Embed Example

```python
# Send rich embed
flow("discord://send_embed?channel_id=123456").with_data({
    "title": "📊 Daily Report",
    "description": "Here's your daily summary",
    "color": 0x00ff00,
    "fields": [
        {"name": "Sales", "value": "$10,000", "inline": True},
        {"name": "Users", "value": "1,234", "inline": True}
    ],
    "footer": "Generated at " + str(datetime.now())
}).run()
```

## Slack Component

### Configuration

```python
# Slack bot token from Slack App
flow("slack://send?channel=general&token=xoxb-YOUR-TOKEN").run("Message")
```

### Operations

| Operation | Description | URI Example |
|-----------|-------------|-------------|
| `send` | Send message | `slack://send?channel=general` |
| `upload` | Upload file | `slack://upload?channel=general` |
| `get_users` | List users | `slack://get_users` |
| `search` | Search messages | `slack://search?query=important` |
| `create_channel` | Create channel | `slack://create_channel?name=new-channel` |

### Interactive Messages

```python
# Send interactive message with buttons
flow("slack://send?channel=approvals").with_data({
    "text": "Approval Required",
    "blocks": [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Request:* New laptop\n*Cost:* $2000"}
        },
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "✅ Approve"}},
                {"type": "button", "text": {"type": "plain_text", "text": "❌ Deny"}}
            ]
        }
    ]
}).run()
```

## SMS Component

### Providers

SMS component supports:
- **Twilio** (Recommended)
- **Vonage** (Nexmo)
- **Plivo**
- **Generic HTTP Gateway**

### Configuration

```python
# Twilio SMS
flow("sms://send"
     "?provider=twilio"
     "&account_sid=YOUR_SID"
     "&auth_token=YOUR_TOKEN"
     "&from_number=+1234567890"
).run({"to": "+0987654321", "message": "Hello!"})

# Vonage SMS
flow("sms://send"
     "?provider=vonage"
     "&api_key=YOUR_KEY"
     "&api_secret=YOUR_SECRET"
).run({"to": "+1234567890", "message": "Hello!"})
```

### Verification System

```python
# Send verification code
result = flow("sms://verify?provider=twilio").run({
    "phone": "+1234567890"
})
print(f"Verification code: {result['verification_code']}")

# Bulk SMS
flow("sms://bulk"
     "?provider=twilio"
     "&numbers=+123,+456,+789"
).run("Broadcast message")
```

## Multi-Channel Examples

### 1. Customer Support System

```python
# Unified support ticket system
support_flow = (
    flow("multicast://parallel=true")
    .destinations([
        "email-watch://folder=support",
        "telegram-bot://token=SUPPORT_BOT",
        "slack-events://channel=support"
    ])
    | "transform://normalize_request"
    | "postgres://insert?table=tickets"
    | "choose://"
      .when("$.priority=='high'", [
          "sms://send?to={{oncall}}",
          "slack://send?channel=urgent"
      ])
      .otherwise("email://send?to=support@company.com")
)
```

### 2. Order Notifications

```python
# Send order confirmation across all channels
order_notification = (
    flow("kafka://consume?topic=orders")
    | "transform://json"
    | "multicast://parallel=true"
    .destinations([
        "email://send?template=order_confirmation",
        "sms://send?message=Order {{id}} confirmed!",
        "whatsapp://template?template=order_confirm",
        "telegram://send?text=✅ Order confirmed!"
    ])
)
```

### 3. Incident Escalation

```python
# Multi-tier escalation
escalation = (
    flow("prometheus://alerts")
    | "filter://severity==critical"
    | "slack://send?channel=incidents"
    | "wait://minutes=5"
    | "choose://"
      .when("$.acknowledged==false", 
            "sms://send?to={{oncall}}")
    | "wait://minutes=10"
    | "choose://"
      .when("$.acknowledged==false",
            "phone://call?to={{manager}}")
)
```

### 4. Marketing Campaign

```python
# Personalized multi-channel campaign
campaign = (
    flow("postgres://query?sql=SELECT * FROM customers")
    | "split://"
    | "enrich://preferences"
    | "choose://"
      .when("$.channel=='email'",
            "email://send?template=campaign")
      .when("$.channel=='sms'",
            "sms://send?message={{offer}}")
      .when("$.channel=='whatsapp'",
            "whatsapp://template?template=promotion")
)
```

## Best Practices

### 1. Error Handling

```python
# Implement fallback channels
notification = (
    flow("email://send?to={{email}}")
    .on_error("sms://send?to={{phone}}")
    .on_error("slack://send?channel=failures")
)
```

### 2. Rate Limiting

```python
# Respect API rate limits
flow("sms://bulk") \
    .with_rate_limit(messages_per_second=1) \
    .run(phone_numbers)
```

### 3. Template Management

```python
# Use templates for consistent messaging
templates = {
    "welcome": "Welcome {{name}}! Your account is ready.",
    "alert": "⚠️ Alert: {{message}} at {{timestamp}}"
}

flow("multicast://") \
    .destinations([
        f"email://send?template={template}",
        f"sms://send?template={template}"
    ])
```

### 4. Delivery Confirmation

```python
# Track delivery status
result = flow("sms://send").run(message)
status = flow("sms://status").run(result['message_id'])
```

### 5. Webhook Security

```python
# Verify webhook signatures
flow("webhook://path=/telegram") \
    | "verify://signature?secret={{webhook_secret}}" \
    | "telegram-webhook://"
```

## Configuration Best Practices

### Environment Variables

```python
import os

# Store sensitive data in environment
flow(f"telegram://send"
     f"?token={os.getenv('TELEGRAM_BOT_TOKEN')}"
     f"&chat_id={os.getenv('TELEGRAM_CHAT_ID')}"
)
```

### Configuration Files

```yaml
# config.yaml
communication:
  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    user: ${EMAIL_USER}
    password: ${EMAIL_PASSWORD}
  
  telegram:
    bot_token: ${TELEGRAM_TOKEN}
  
  twilio:
    account_sid: ${TWILIO_SID}
    auth_token: ${TWILIO_TOKEN}
```

### Connection Pooling

```python
# Reuse connections for better performance
email_pool = flow("email://pool?max_connections=10")
for message in messages:
    email_pool.send(message)
```

## Testing

### Unit Tests

```python
from unittest.mock import patch

@patch('requests.post')
def test_telegram_send(mock_post):
    mock_post.return_value.json.return_value = {"ok": True}
    
    result = flow("telegram://send?chat_id=123").run("Test")
    assert result["ok"] == True
```

### Integration Tests

```python
# Test with real services (use test accounts)
def test_multi_channel_integration():
    test_message = "Integration test at " + str(datetime.now())
    
    results = flow("multicast://").destinations([
        "slack://send?channel=test",
        "email://send?to=test@example.com"
    ]).run(test_message)
    
    assert all(r["success"] for r in results)
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify API tokens are correct
   - Check token permissions/scopes
   - Ensure tokens are not expired

2. **Rate Limiting**
   - Implement exponential backoff
   - Use bulk operations where available
   - Cache frequently accessed data

3. **Message Formatting**
   - Escape special characters for each platform
   - Respect message length limits
   - Use platform-specific formatting

4. **Webhook Issues**
   - Verify webhook URL is publicly accessible
   - Check SSL certificates
   - Implement webhook verification

## Support

For issues and questions:
- GitHub Issues: https://github.com/softreck/streamware/issues
- Documentation: https://streamware.readthedocs.io
- Email: support@streamware.io
