# Communication Examples

Email, Slack, Telegram, Discord, WhatsApp, SMS integration.

## 📁 Examples

| File | Description |
|------|-------------|
| [send_email.py](send_email.py) | Send emails with SMTP |
| [slack_bot.py](slack_bot.py) | Slack messaging and bots |
| [telegram_bot.py](telegram_bot.py) | Telegram bot commands |
| [discord_webhook.py](discord_webhook.py) | Discord webhooks |
| [multi_channel.py](multi_channel.py) | Broadcast to all channels |

## 🚀 Quick Start

```bash
# Send email
sq email user@example.com --subject "Hello" --body "Message" --smtp smtp.gmail.com

# Slack message
sq slack general --message "Hello team!"

# Telegram
sq telegram @channel --message "Update!"

# Discord webhook
sq discord --webhook URL --message "Alert!"

# SMS
sq sms +1234567890 --message "Hello" --provider twilio
```

## 🔧 Configuration

```bash
# Email
export SMTP_HOST=smtp.gmail.com
export SMTP_USER=user@gmail.com
export SMTP_PASSWORD=app_password

# Slack
export SLACK_TOKEN=xoxb-...

# Telegram
export TELEGRAM_BOT_TOKEN=123456:ABC...

# Discord
export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## 📚 Related Documentation

- [Communication Component](../../docs/v2/components/COMMUNICATION.md)
- [Quick CLI](../../docs/v2/components/QUICK_CLI.md)

## 🔗 Related Examples

- [Automation](../automation/) - Automated notifications
- [Data Pipelines](../data-pipelines/) - ETL alerts

## 🔗 Source Code

- [streamware/components/email.py](../../streamware/components/email.py)
- [streamware/components/slack.py](../../streamware/components/slack.py)
- [streamware/components/telegram.py](../../streamware/components/telegram.py)
- [streamware/components/discord.py](../../streamware/components/discord.py)
