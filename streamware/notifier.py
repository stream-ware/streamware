"""
Streamware Notification Module
Handles sending notifications (email, slack, telegram, webhook) based on intent config.

Usage:
    from streamware.notifier import Notifier
    
    notifier = Notifier.from_intent(intent)
    notifier.add_event("Person detected", screenshot_path="/tmp/frame.jpg")
    notifier.flush()  # Send pending notifications
"""

import time
import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import threading
import requests
from datetime import datetime

from .config import config

# Setup notification logger
logger = logging.getLogger("streamware.notifier")

def _get_log_path() -> Path:
    """Get path for notification log file."""
    reports_dir = Path(config.get("SQ_REPORTS_DIR", "./reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir / "notifications.log"

def _log_notification(channel: str, recipient: str, status: str, message: str, error: str = None):
    """Log notification attempt to file."""
    log_path = _get_log_path()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "channel": channel,
        "recipient": recipient,
        "status": status,
        "message": message[:100],
    }
    if error:
        log_entry["error"] = str(error)
    
    # Append to log file
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    # Also log to console logger
    if status == "success":
        logger.info(f"{channel} → {recipient}: {status}")
    else:
        logger.warning(f"{channel} → {recipient}: {status} - {error}")


@dataclass
class NotificationEvent:
    """Single notification event."""
    timestamp: float
    message: str
    screenshot_path: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class Notifier:
    """
    Notification manager supporting multiple channels and batching.
    
    Modes:
        - instant: Send immediately on each event
        - digest: Batch events and send every N seconds
        - summary: Only send at the end (flush)
    """
    
    def __init__(
        self,
        email: Optional[str] = None,
        slack: Optional[str] = None,
        telegram: Optional[str] = None,
        webhook: Optional[str] = None,
        mode: str = "digest",
        interval: int = 60,
        cooldown: int = 300,
    ):
        self.email = email
        self.slack = slack
        self.telegram = telegram
        self.webhook = webhook
        self.mode = mode
        self.interval = interval
        self.cooldown = cooldown
        
        # Event buffer
        self._events: List[NotificationEvent] = []
        self._last_send_time: float = 0
        self._last_message: str = ""
        self._lock = threading.Lock()
        
        # SMTP config from .env
        self.smtp_host = config.get("SQ_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(config.get("SQ_SMTP_PORT", "587"))
        self.smtp_user = config.get("SQ_SMTP_USER", "")
        self.smtp_pass = config.get("SQ_SMTP_PASS", "")
        self.smtp_from = config.get("SQ_SMTP_FROM", self.smtp_user)
        
        # Timer for digest mode OR instant mode (for buffered events)
        self._timer: Optional[threading.Timer] = None
        if mode == "digest" and interval > 0:
            self._start_timer()
        elif mode == "instant":
            # In instant mode, flush buffered events every 10 seconds
            self._start_timer(interval=10)
    
    @classmethod
    def from_intent(cls, intent) -> "Notifier":
        """Create notifier from parsed intent."""
        return cls(
            email=intent.notify_email,
            slack=intent.notify_slack,
            telegram=intent.notify_telegram,
            webhook=intent.notify_webhook,
            mode=intent.notify_mode,
            interval=intent.notify_interval,
            cooldown=intent.notify_cooldown,
        )
    
    @classmethod
    def from_config(cls) -> "Notifier":
        """Create notifier from environment config."""
        # Get email from intent or fall back to saved SQ_EMAIL_TO
        email = config.get("SQ_NOTIFY_EMAIL") or config.get("SQ_EMAIL_TO") or None
        slack = config.get("SQ_NOTIFY_SLACK") or config.get("SQ_SLACK_CHANNEL") or None
        telegram = config.get("SQ_NOTIFY_TELEGRAM") or config.get("SQ_TELEGRAM_CHAT_ID") or None
        webhook = config.get("SQ_NOTIFY_WEBHOOK") or config.get("SQ_WEBHOOK_URL") or None
        
        return cls(
            email=email if email else None,
            slack=slack if slack and slack != "alerts" else None,  # Skip default
            telegram=telegram if telegram else None,
            webhook=webhook if webhook else None,
            mode=config.get("SQ_NOTIFY_MODE", "digest"),
            interval=int(config.get("SQ_NOTIFY_INTERVAL", "60")),
            cooldown=int(config.get("SQ_NOTIFY_COOLDOWN", "300")),
        )
    
    def _start_timer(self, interval: Optional[int] = None):
        """Start digest/flush timer."""
        if self._timer:
            self._timer.cancel()
        timer_interval = interval if interval is not None else self.interval
        self._timer = threading.Timer(timer_interval, self._timer_callback)
        self._timer.daemon = True
        self._timer.start()
    
    def _timer_callback(self):
        """Called when digest timer fires."""
        self.flush()
        # Restart timer with appropriate interval
        if self.mode == "instant":
            self._start_timer(interval=10)
        else:
            self._start_timer()
    
    def add_event(self, message: str, screenshot_path: Optional[str] = None, **details):
        """Add an event to the notification queue."""
        now = time.time()
        
        # Instant mode: minimum 10 seconds between emails to prevent spam
        if self.mode == "instant":
            min_interval = 10  # seconds
            if (now - self._last_send_time) < min_interval:
                # Buffer this event instead of sending immediately
                event = NotificationEvent(
                    timestamp=now,
                    message=message,
                    screenshot_path=screenshot_path,
                    details=details,
                )
                with self._lock:
                    self._events.append(event)
                return  # Don't send yet
        
        # Cooldown check - skip duplicate messages within cooldown period
        if message == self._last_message and (now - self._last_send_time) < self.cooldown:
            return
        
        event = NotificationEvent(
            timestamp=now,
            message=message,
            screenshot_path=screenshot_path,
            details=details,
        )
        
        with self._lock:
            self._events.append(event)
        
        # Instant mode: send immediately (but respecting min interval above)
        if self.mode == "instant":
            self.flush()
    
    def flush(self):
        """Send all pending notifications."""
        with self._lock:
            if not self._events:
                return
            
            events = self._events.copy()
            self._events.clear()
        
        if not events:
            return
        
        # Build message
        if len(events) == 1:
            subject = f"🎯 Alert: {events[0].message}"
            body = self._format_single_event(events[0])
        else:
            subject = f"🎯 Alert: {len(events)} events detected"
            body = self._format_digest(events)
        
        # Send to all channels
        screenshot = events[-1].screenshot_path if events else None
        
        if self.email:
            self._send_email(subject, body, screenshot)
        
        if self.slack:
            self._send_slack(subject, body)
        
        if self.telegram:
            self._send_telegram(body, screenshot)
        
        if self.webhook:
            self._send_webhook(events)
        
        # Update last send time for rate limiting
        self._last_send_time = time.time()
        if events:
            self._last_message = events[-1].message
    
    def _format_single_event(self, event: NotificationEvent) -> str:
        """Format a single event for notification."""
        lines = [
            f"📹 Streamware Detection Alert",
            f"",
            f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event.timestamp))}",
            f"Event: {event.message}",
        ]
        if event.details:
            lines.append("")
            for key, value in event.details.items():
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    def _format_digest(self, events: List[NotificationEvent]) -> str:
        """Format multiple events as digest."""
        lines = [
            f"📹 Streamware Detection Digest",
            f"",
            f"Events: {len(events)}",
            f"Period: {time.strftime('%H:%M:%S', time.localtime(events[0].timestamp))} - {time.strftime('%H:%M:%S', time.localtime(events[-1].timestamp))}",
            f"",
            "Events:",
        ]
        for event in events:
            t = time.strftime('%H:%M:%S', time.localtime(event.timestamp))
            lines.append(f"  [{t}] {event.message}")
        return "\n".join(lines)
    
    def _send_email(self, subject: str, body: str, screenshot: Optional[str] = None):
        """Send email notification."""
        if not self.smtp_user or not self.smtp_pass:
            print(f"⚠️  Email not configured (set SQ_SMTP_USER and SQ_SMTP_PASS)")
            _log_notification("email", self.email, "skipped", subject, "SMTP credentials not configured")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_from
            msg['To'] = self.email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach screenshot if available
            if screenshot and Path(screenshot).exists():
                with open(screenshot, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-Disposition', 'attachment', filename='detection.jpg')
                    msg.attach(img)
            
            # Send - use SSL for port 465, STARTTLS for port 587
            if self.smtp_port == 465:
                # SSL connection
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # STARTTLS connection (port 587)
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            
            print(f"📧 Email sent to {self.email}")
            _log_notification("email", self.email, "success", subject)
        except Exception as e:
            print(f"❌ Email failed: {e}")
            _log_notification("email", self.email, "failed", subject, str(e))
    
    def _send_slack(self, subject: str, body: str):
        """Send Slack notification."""
        webhook_url = config.get("SQ_SLACK_WEBHOOK")
        if not webhook_url:
            print(f"⚠️  Slack not configured (set SQ_SLACK_WEBHOOK)")
            _log_notification("slack", self.slack, "skipped", subject, "Webhook not configured")
            return
        
        try:
            payload = {
                "channel": self.slack,
                "text": f"*{subject}*\n```{body}```",
            }
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.ok:
                print(f"💬 Slack sent to {self.slack}")
                _log_notification("slack", self.slack, "success", subject)
            else:
                print(f"❌ Slack failed: {response.text}")
                _log_notification("slack", self.slack, "failed", subject, response.text)
        except Exception as e:
            print(f"❌ Slack failed: {e}")
            _log_notification("slack", self.slack, "failed", subject, str(e))
    
    def _send_telegram(self, body: str, screenshot: Optional[str] = None):
        """Send Telegram notification."""
        bot_token = config.get("SQ_TELEGRAM_BOT_TOKEN")
        if not bot_token:
            print(f"⚠️  Telegram not configured (set SQ_TELEGRAM_BOT_TOKEN)")
            _log_notification("telegram", self.telegram, "skipped", body[:50], "Bot token not configured")
            return
        
        try:
            chat_id = self.telegram
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": body}
            response = requests.post(url, json=payload, timeout=10)
            
            if response.ok:
                print(f"📱 Telegram sent to {chat_id}")
                _log_notification("telegram", chat_id, "success", body[:50])
                
                # Send screenshot if available
                if screenshot and Path(screenshot).exists():
                    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                    with open(screenshot, 'rb') as f:
                        requests.post(url, data={"chat_id": chat_id}, files={"photo": f}, timeout=30)
            else:
                print(f"❌ Telegram failed: {response.text}")
                _log_notification("telegram", chat_id, "failed", body[:50], response.text)
        except Exception as e:
            print(f"❌ Telegram failed: {e}")
            _log_notification("telegram", self.telegram, "failed", body[:50], str(e))
    
    def _send_webhook(self, events: List[NotificationEvent]):
        """Send webhook notification."""
        message = events[0].message if events else "notification"
        try:
            payload = {
                "source": "streamware",
                "timestamp": time.time(),
                "events": [
                    {
                        "time": e.timestamp,
                        "message": e.message,
                        "details": e.details,
                    }
                    for e in events
                ],
            }
            response = requests.post(self.webhook, json=payload, timeout=10)
            if response.ok:
                print(f"🔗 Webhook sent to {self.webhook[:30]}...")
                _log_notification("webhook", self.webhook[:50], "success", message)
            else:
                print(f"❌ Webhook failed: {response.status_code}")
                _log_notification("webhook", self.webhook[:50], "failed", message, f"HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Webhook failed: {e}")
            _log_notification("webhook", self.webhook[:50], "failed", message, str(e))
    
    def stop(self):
        """Stop the notifier and send final notifications."""
        if self._timer:
            self._timer.cancel()
        self.flush()
    
    def has_channels(self) -> bool:
        """Check if any notification channel is configured."""
        return bool(self.email or self.slack or self.telegram or self.webhook)


# Convenience function
def notify(message: str, **kwargs):
    """Send a one-off notification using config settings."""
    notifier = Notifier.from_config()
    if notifier.has_channels():
        notifier.add_event(message, **kwargs)
        notifier.flush()
    else:
        print(f"ℹ️  No notification channels configured")
