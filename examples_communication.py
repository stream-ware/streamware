"""
Streamware Communication Examples - Email, Telegram, WhatsApp, Discord, Slack, SMS
"""

import asyncio
from streamware import flow


# ========== EMAIL EXAMPLES ==========

def example_email_send():
    """Send email with attachments"""
    print("=== Email: Send with Attachments ===")
    
    result = (
        flow("email://send?to=user@example.com&subject=Report")
        .with_data({
            "body": "Please find the attached report.",
            "attachments": ["report.pdf", "data.xlsx"],
            "html": "<h1>Monthly Report</h1><p>Please review the attached files.</p>"
        })
    ).run()
    
    print(f"Email sent: {result}")


def example_email_automation():
    """Email automation pipeline"""
    print("=== Email: Automated Response System ===")
    
    # Watch inbox, filter, and auto-respond
    pipeline = (
        flow("email-watch://interval=30")
        | "email-filter://subject=Support"
        | "transform://template?template=Dear {{from}}, we received your request..."
        | "email://send"
    )
    
    # Process first 5 emails
    for i, result in enumerate(pipeline.stream()):
        print(f"Processed email {i+1}: {result}")
        if i >= 4:
            break


def example_email_to_ticket():
    """Convert emails to support tickets"""
    print("=== Email to Ticket System ===")
    
    result = (
        flow("email://read?folder=INBOX&unread=true")
        | "filter://predicate=$.subject contains 'Bug'"
        | "transform://jsonpath?query=$[*].{title:subject,description:body,email:from}"
        | "postgres://insert?table=tickets"
        | "email://send?template=ticket_confirmation"
    ).run()
    
    print(f"Created {len(result)} tickets from emails")


# ========== TELEGRAM EXAMPLES ==========

def example_telegram_bot():
    """Telegram bot with commands"""
    print("=== Telegram: Bot with Commands ===")
    
    # Bot that responds to commands
    pipeline = (
        flow("telegram-bot://token=YOUR_BOT_TOKEN")
        | "telegram-command://"
        | "choose://"
          "?when1=$.command=='/start'&then1=telegram://send?text=Welcome!"
          "&when2=$.command=='/help'&then2=telegram://send?text=Available commands..."
          "&otherwise=telegram://send?text=Unknown command"
    )
    
    # Simulate processing commands
    commands = [
        {"message": {"text": "/start", "chat": {"id": 123}}},
        {"message": {"text": "/help", "chat": {"id": 123}}},
        {"message": {"text": "/unknown", "chat": {"id": 123}}}
    ]
    
    for cmd in commands:
        result = pipeline.run(cmd)
        print(f"Bot response: {result}")


def example_telegram_broadcast():
    """Broadcast to Telegram channels"""
    print("=== Telegram: Broadcast System ===")
    
    # Get data and broadcast to multiple channels
    result = (
        flow("http://api.example.com/news/latest")
        | "transform://template?template=📰 **{{title}}**\n\n{{summary}}\n\n[Read more]({{url}})"
        | "multicast://destinations="
          "telegram://send?chat_id=@channel1,"
          "telegram://send?chat_id=@channel2,"
          "telegram://send?chat_id=@channel3"
    ).run()
    
    print(f"Broadcasted to {len(result)} channels")


def example_telegram_media_pipeline():
    """Process and send media via Telegram"""
    print("=== Telegram: Media Processing Pipeline ===")
    
    # Download image, process, and send
    result = (
        flow("http://api.example.com/image-of-the-day")
        | "download://path=/tmp/image.jpg"
        | "transform://image_resize?width=1024"
        | "telegram://send_photo?chat_id=@photos_channel&caption=Image of the Day"
    ).run()
    
    print(f"Media sent: {result}")


# ========== WHATSAPP EXAMPLES ==========

def example_whatsapp_customer_service():
    """WhatsApp customer service automation"""
    print("=== WhatsApp: Customer Service Bot ===")
    
    # Auto-respond to customer messages
    result = (
        flow("whatsapp-webhook://")
        | "curllm://extract?instruction=Determine customer intent and suggested response"
        | "whatsapp://template?template=customer_response"
    ).run({
        "messages": [{
            "from": "+1234567890",
            "text": "I need help with my order #12345"
        }]
    })
    
    print(f"Customer service response: {result}")


def example_whatsapp_order_notifications():
    """Send order notifications via WhatsApp"""
    print("=== WhatsApp: Order Notifications ===")
    
    # Send order updates to customers
    orders = [
        {"phone": "+1234567890", "order_id": "12345", "status": "shipped"},
        {"phone": "+0987654321", "order_id": "67890", "status": "delivered"}
    ]
    
    for order in orders:
        result = (
            flow("whatsapp://template?template=order_update")
            .with_data({
                "phone": order["phone"],
                "parameters": [order["order_id"], order["status"]]
            })
        ).run()
        
        print(f"Notification sent for order {order['order_id']}: {result}")


def example_whatsapp_broadcast_campaign():
    """WhatsApp marketing campaign"""
    print("=== WhatsApp: Broadcast Campaign ===")
    
    # Get customer list and send campaign
    result = (
        flow("postgres://query?sql=SELECT phone FROM customers WHERE opted_in=true")
        | "split://"
        | "whatsapp://send?message=🎉 Special offer just for you! Get 20% off today."
        | "join://strategy=list"
        | "postgres://insert?table=campaign_results"
    ).run()
    
    print(f"Campaign sent to {len(result)} customers")


# ========== DISCORD EXAMPLES ==========

def example_discord_announcement():
    """Discord server announcement system"""
    print("=== Discord: Server Announcement ===")
    
    # Send announcement with embed
    result = (
        flow("discord://send_embed?channel_id=123456789")
        .with_data({
            "title": "🚀 New Release!",
            "description": "Version 2.0 is now available",
            "color": 0x00ff00,
            "fields": [
                {"name": "Features", "value": "• Feature 1\n• Feature 2", "inline": True},
                {"name": "Download", "value": "[Click here](https://example.com)", "inline": True}
            ],
            "footer": "Released on " + str(datetime.now())
        })
    ).run()
    
    print(f"Announcement sent: {result}")


def example_discord_moderation():
    """Discord moderation pipeline"""
    print("=== Discord: Auto-Moderation ===")
    
    # Monitor messages and moderate
    pipeline = (
        flow("discord-bot://token=BOT_TOKEN")
        | "curllm://extract?instruction=Check for inappropriate content"
        | "choose://"
          "?when1=$.inappropriate==true&then1=discord://delete_message"
          "&when2=$.warning==true&then2=discord://send?content=Please follow community guidelines"
          "&otherwise=discord://add_reaction?emoji=✅"
    )
    
    # Simulate message moderation
    message = {
        "content": "Check this cool link!",
        "channel_id": "123456",
        "message_id": "789012",
        "author": {"id": "345678"}
    }
    
    result = pipeline.run(message)
    print(f"Moderation action: {result}")


def example_discord_webhook_logger():
    """Log events to Discord via webhook"""
    print("=== Discord: Webhook Logger ===")
    
    # Monitor system and log to Discord
    result = (
        flow("file-watch://path=/var/log/app&pattern=*.error")
        | "file://read"
        | "transform://template?template=⚠️ **Error Detected**\n```{{content}}```"
        | "discord://webhook?url=https://discord.com/api/webhooks/..."
    ).run()
    
    print(f"Error logged to Discord: {result}")


# ========== SLACK EXAMPLES ==========

def example_slack_standup():
    """Slack daily standup collector"""
    print("=== Slack: Daily Standup Bot ===")
    
    # Collect standup updates
    result = (
        flow("slack://send?channel=team-standup")
        .with_data({
            "text": "Good morning! Time for daily standup. Please share:",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "📝 *Daily Standup*"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "• What did you do yesterday?\n• What will you do today?\n• Any blockers?"}
                }
            ]
        })
    ).run()
    
    print(f"Standup prompt sent: {result}")


def example_slack_incident_response():
    """Slack incident response automation"""
    print("=== Slack: Incident Response ===")
    
    # Detect incident and coordinate response
    incident_data = {
        "severity": "high",
        "service": "payment-api",
        "error_rate": 15.5,
        "timestamp": "2024-01-20 14:30:00"
    }
    
    result = (
        flow("slack://create_channel?name=incident-{timestamp}")
        | "slack://send?text=@here Incident detected in {service}"
        | "multicast://destinations="
          "pagerduty://create_incident,"
          "jira://create_issue?type=incident,"
          "slack://send?channel=incidents-log"
    ).run(incident_data)
    
    print(f"Incident response initiated: {result}")


def example_slack_workflow():
    """Slack approval workflow"""
    print("=== Slack: Approval Workflow ===")
    
    # Request approval via Slack
    approval_request = {
        "requester": "john.doe",
        "item": "New laptop",
        "cost": "$2000",
        "justification": "Current laptop is 5 years old"
    }
    
    result = (
        flow("slack://send?channel=approvals")
        .with_data({
            "text": "Approval Required",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Request from:* {approval_request['requester']}\n*Item:* {approval_request['item']}\n*Cost:* {approval_request['cost']}"}
                },
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "✅ Approve"}, "value": "approve"},
                        {"type": "button", "text": {"type": "plain_text", "text": "❌ Deny"}, "value": "deny"}
                    ]
                }
            ]
        })
        | "slack-events://wait_for_interaction"
        | "choose://"
          "?when1=$.value=='approve'&then1=email://send?to=finance@company.com"
          "&otherwise=email://send?to=requester@company.com&subject=Request Denied"
    ).run()
    
    print(f"Approval workflow initiated: {result}")


# ========== SMS EXAMPLES ==========

def example_sms_verification():
    """SMS verification system"""
    print("=== SMS: Verification System ===")
    
    # Send verification code
    user_phone = "+1234567890"
    
    result = (
        flow("sms://verify?provider=twilio")
        .with_data({
            "phone": user_phone,
            "code": None  # Auto-generate
        })
    ).run()
    
    print(f"Verification sent: {result}")
    
    # Store code in cache for verification
    cache_result = (
        flow("redis://set?key=verify:{phone}&expire=300")
        .with_data({
            "phone": user_phone,
            "value": result["verification_code"]
        })
    ).run()
    
    print(f"Code cached: {cache_result}")


def example_sms_alert_system():
    """SMS alert system for critical events"""
    print("=== SMS: Alert System ===")
    
    # Monitor system and send SMS alerts
    alert_pipeline = (
        flow("prometheus://query?metric=error_rate")
        | "filter://predicate=$.value>10"
        | "transform://template?template=ALERT: Error rate is {{value}}% on {{service}}"
        | "sms://bulk?provider=twilio&numbers=+1234567890,+0987654321"
    )
    
    # Simulate alert
    metric_data = {"value": 15.5, "service": "payment-api"}
    result = alert_pipeline.run(metric_data)
    
    print(f"Alerts sent: {result}")


def example_sms_appointment_reminder():
    """SMS appointment reminder system"""
    print("=== SMS: Appointment Reminders ===")
    
    # Get appointments and send reminders
    result = (
        flow("postgres://query?sql=SELECT * FROM appointments WHERE date=TOMORROW()")
        | "split://"
        | "transform://template?template=Reminder: Your appointment is tomorrow at {{time}}. Reply YES to confirm."
        | "sms://send?provider=vonage"
        | "join://strategy=list"
    ).run()
    
    print(f"Sent {len(result)} appointment reminders")


# ========== MULTI-CHANNEL EXAMPLES ==========

def example_multi_channel_notification():
    """Send notifications across multiple channels"""
    print("=== Multi-Channel: Notification System ===")
    
    notification = {
        "title": "System Maintenance",
        "message": "Scheduled maintenance on Saturday 2AM-4AM UTC",
        "priority": "high"
    }
    
    result = (
        flow("transform://enrich?timestamp=now")
        | "multicast://destinations="
          "email://send?to=all@company.com&subject={{title}},"
          "slack://send?channel=general,"
          "telegram://send?chat_id=@company_updates,"
          "discord://webhook?url=WEBHOOK_URL,"
          "sms://bulk?numbers={{admin_phones}}"
    ).run(notification)
    
    print(f"Notification sent to {len(result)} channels")


def example_customer_journey():
    """Complete customer journey across channels"""
    print("=== Multi-Channel: Customer Journey ===")
    
    customer = {
        "email": "customer@example.com",
        "phone": "+1234567890",
        "telegram": "@customer",
        "name": "John Doe"
    }
    
    # Welcome flow
    welcome_flow = (
        flow("email://send?subject=Welcome {{name}}!")
        | "sms://send?message=Thanks for joining! Check your email for details."
        | "wait://seconds=3600"  # Wait 1 hour
        | "telegram://send?text=Hi {{name}}, how's your experience so far?"
    )
    
    result = welcome_flow.run(customer)
    print(f"Customer journey completed: {result}")


def example_alert_escalation():
    """Alert escalation across channels"""
    print("=== Multi-Channel: Alert Escalation ===")
    
    alert = {
        "severity": "critical",
        "service": "database",
        "message": "Database connection pool exhausted"
    }
    
    # Escalation chain
    escalation_flow = (
        flow("slack://send?channel=ops-alerts")
        | "wait://seconds=300"  # Wait 5 minutes
        | "choose://"
          "?when=$.acknowledged==false&then=sms://send?to={{oncall_phone}}"
        | "wait://seconds=300"
        | "choose://"
          "?when=$.acknowledged==false&then=phone://call?to={{manager_phone}}"
    )
    
    result = escalation_flow.run(alert)
    print(f"Escalation result: {result}")


# ========== CHATBOT EXAMPLES ==========

def example_unified_chatbot():
    """Unified chatbot across all platforms"""
    print("=== Unified Chatbot ===")
    
    # Single chatbot logic for all platforms
    chatbot_flow = (
        flow("curllm://chat?model=gpt-4")
        | "transform://format_response"
        | "choose://"
          "?when=$.platform=='telegram'&then=telegram://send"
          "&when=$.platform=='discord'&then=discord://send"
          "&when=$.platform=='slack'&then=slack://send"
          "&when=$.platform=='whatsapp'&then=whatsapp://send"
    )
    
    # Process message from any platform
    message = {
        "text": "What's the weather like?",
        "platform": "telegram",
        "chat_id": "123456"
    }
    
    result = chatbot_flow.run(message)
    print(f"Chatbot response: {result}")


# ========== RUN ALL EXAMPLES ==========

if __name__ == "__main__":
    from datetime import datetime
    
    examples = [
        # Email
        example_email_send,
        example_email_to_ticket,
        
        # Telegram
        example_telegram_bot,
        example_telegram_broadcast,
        
        # WhatsApp
        example_whatsapp_customer_service,
        example_whatsapp_order_notifications,
        
        # Discord
        example_discord_announcement,
        example_discord_webhook_logger,
        
        # Slack
        example_slack_standup,
        example_slack_workflow,
        
        # SMS
        example_sms_verification,
        example_sms_appointment_reminder,
        
        # Multi-channel
        example_multi_channel_notification,
        example_unified_chatbot
    ]
    
    print("=" * 60)
    print("STREAMWARE COMMUNICATION EXAMPLES")
    print("=" * 60)
    
    for example in examples:
        try:
            print(f"\nRunning: {example.__name__}")
            print("-" * 40)
            example()
        except Exception as e:
            print(f"Example {example.__name__} failed: {e}")
        
        print()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
