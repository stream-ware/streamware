"""
Shared Webhook Utilities for Streamware

Provides common webhook functionality to reduce code duplication across components.
"""

import logging
import requests
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def send_webhook(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
    method: str = "POST",
) -> Dict[str, Any]:
    """Send a webhook request.
    
    Args:
        url: Webhook URL
        payload: JSON payload to send
        headers: Optional headers
        timeout: Request timeout in seconds
        method: HTTP method (POST, PUT, etc.)
        
    Returns:
        Response JSON or empty dict on failure
    """
    if not url:
        logger.warning("No webhook URL provided")
        return {}
    
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    try:
        response = requests.request(
            method=method,
            url=url,
            json=payload,
            headers=default_headers,
            timeout=timeout,
        )
        response.raise_for_status()
        
        try:
            return response.json()
        except ValueError:
            return {"status": "ok", "code": response.status_code}
            
    except requests.exceptions.Timeout:
        logger.warning(f"Webhook timeout: {url}")
        return {"error": "timeout"}
    except requests.exceptions.RequestException as e:
        logger.warning(f"Webhook failed: {e}")
        return {"error": str(e)}


def send_discord_webhook(
    url: str,
    content: str,
    username: str = "Streamware",
    avatar_url: Optional[str] = None,
    embeds: Optional[list] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """Send a Discord webhook message.
    
    Args:
        url: Discord webhook URL
        content: Message content
        username: Bot username
        avatar_url: Optional avatar URL
        embeds: Optional embeds list
        timeout: Request timeout
        
    Returns:
        Response dict
    """
    payload = {
        "content": content,
        "username": username,
    }
    
    if avatar_url:
        payload["avatar_url"] = avatar_url
    if embeds:
        payload["embeds"] = embeds
    
    return send_webhook(url, payload, timeout=timeout)


def send_slack_webhook(
    url: str,
    text: str,
    channel: Optional[str] = None,
    username: str = "Streamware",
    icon_emoji: str = ":robot_face:",
    attachments: Optional[list] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """Send a Slack webhook message.
    
    Args:
        url: Slack webhook URL
        text: Message text
        channel: Optional channel override
        username: Bot username
        icon_emoji: Bot emoji icon
        attachments: Optional attachments
        timeout: Request timeout
        
    Returns:
        Response dict
    """
    payload = {
        "text": text,
        "username": username,
        "icon_emoji": icon_emoji,
    }
    
    if channel:
        payload["channel"] = channel
    if attachments:
        payload["attachments"] = attachments
    
    return send_webhook(url, payload, timeout=timeout)


def send_teams_webhook(
    url: str,
    title: str,
    text: str,
    theme_color: str = "0076D7",
    timeout: int = 10,
) -> Dict[str, Any]:
    """Send a Microsoft Teams webhook message.
    
    Args:
        url: Teams webhook URL
        title: Card title
        text: Message text
        theme_color: Card color (hex)
        timeout: Request timeout
        
    Returns:
        Response dict
    """
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": theme_color,
        "summary": title,
        "sections": [{
            "activityTitle": title,
            "text": text,
        }],
    }
    
    return send_webhook(url, payload, timeout=timeout)
