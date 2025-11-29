"""
Slack Component for Streamware - Slack API integration
"""

import json
import requests
from typing import Any, Optional, Iterator, Dict, List
import time
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    logger.debug("slack-sdk not installed. Using HTTP API fallback.")


@register("slack")
class SlackComponent(Component):
    """
    Slack component for sending messages and workspace operations
    
    URI formats:
        slack://send?channel=general&token=xoxb-...
        slack://post_thread?channel=C123&thread_ts=123.456
        slack://upload?channel=general&file=path/to/file.pdf
        slack://get_users?token=xoxb-...
        slack://search?query=important&token=xoxb-...
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "send"
        self.token = uri.get_param('token', uri.get_param('bot_token'))
        self.api_url = "https://slack.com/api"
        
        if not self.token:
            logger.warning("Slack token not provided. Some operations may fail.")
            
    def process(self, data: Any) -> Any:
        """Process Slack operation"""
        if self.operation == "send":
            return self._send_message(data)
        elif self.operation == "post_thread":
            return self._post_thread_reply(data)
        elif self.operation == "upload":
            return self._upload_file(data)
        elif self.operation == "get_users":
            return self._get_users()
        elif self.operation == "get_channels":
            return self._get_channels()
        elif self.operation == "search":
            return self._search(data)
        elif self.operation == "add_reaction":
            return self._add_reaction(data)
        elif self.operation == "create_channel":
            return self._create_channel(data)
        else:
            raise ComponentError(f"Unknown Slack operation: {self.operation}")
            
    def _send_message(self, data: Any) -> Dict[str, Any]:
        """Send message to Slack channel"""
        channel = self.uri.get_param('channel')
        
        if isinstance(data, dict):
            channel = channel or data.get('channel')
            text = data.get('text', data.get('message', ''))
            blocks = data.get('blocks')
            attachments = data.get('attachments')
            thread_ts = data.get('thread_ts')
        else:
            text = str(data) if data else ''
            blocks = None
            attachments = None
            thread_ts = None
            
        if not channel:
            raise ComponentError("Channel not specified")
        if not self.token:
            raise ComponentError("Slack token not specified")
            
        # Format channel (add # if needed)
        if not channel.startswith(('#', '@', 'C', 'D', 'G')):
            channel = f"#{channel}"
            
        if SLACK_SDK_AVAILABLE:
            return self._send_with_sdk(channel, text, blocks, attachments, thread_ts)
        else:
            return self._send_with_http(channel, text, blocks, attachments, thread_ts)
            
    def _send_with_sdk(self, channel: str, text: str, blocks: Any, attachments: Any, thread_ts: str) -> Dict[str, Any]:
        """Send message using Slack SDK"""
        try:
            client = WebClient(token=self.token)
            
            kwargs = {
                "channel": channel,
                "text": text
            }
            
            if blocks:
                kwargs["blocks"] = blocks
            if attachments:
                kwargs["attachments"] = attachments
            if thread_ts:
                kwargs["thread_ts"] = thread_ts
                
            response = client.chat_postMessage(**kwargs)
            
            return {
                "success": True,
                "channel": response["channel"],
                "ts": response["ts"],
                "message": text[:100] + "..." if len(text) > 100 else text
            }
            
        except SlackApiError as e:
            raise ConnectionError(f"Slack API error: {e.response['error']}")
            
    def _send_with_http(self, channel: str, text: str, blocks: Any, attachments: Any, thread_ts: str) -> Dict[str, Any]:
        """Send message using HTTP API"""
        url = f"{self.api_url}/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": channel,
            "text": text
        }
        
        if blocks:
            payload["blocks"] = blocks
        if attachments:
            payload["attachments"] = attachments
        if thread_ts:
            payload["thread_ts"] = thread_ts
            
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                return {
                    "success": True,
                    "channel": result["channel"],
                    "ts": result["ts"],
                    "message": text[:100] + "..." if len(text) > 100 else text
                }
            else:
                raise ConnectionError(f"Slack API error: {result.get('error')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Slack request failed: {e}")
            
    def _post_thread_reply(self, data: Any) -> Dict[str, Any]:
        """Post a reply to a thread"""
        if isinstance(data, dict):
            data["thread_ts"] = data.get("thread_ts") or self.uri.get_param("thread_ts")
        return self._send_message(data)
        
    def _upload_file(self, data: Any) -> Dict[str, Any]:
        """Upload file to Slack"""
        channel = self.uri.get_param('channel')
        
        if isinstance(data, dict):
            channel = channel or data.get('channel')
            file_path = data.get('file', data.get('file_path'))
            title = data.get('title', '')
            comment = data.get('comment', data.get('initial_comment', ''))
        else:
            file_path = self.uri.get_param('file')
            title = self.uri.get_param('title', '')
            comment = self.uri.get_param('comment', '')
            
        if not channel:
            raise ComponentError("Channel not specified")
        if not file_path:
            raise ComponentError("File path not specified")
        if not self.token:
            raise ComponentError("Slack token not specified")
            
        # Format channel
        if not channel.startswith(('#', '@', 'C', 'D', 'G')):
            channel = f"#{channel}"
            
        from pathlib import Path
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ComponentError(f"File not found: {file_path}")
            
        url = f"{self.api_url}/files.upload"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'channels': channel,
                'title': title or file_path.name,
                'initial_comment': comment
            }
            
            try:
                response = requests.post(url, headers=headers, data=data, files=files)
                response.raise_for_status()
                result = response.json()
                
                if result.get("ok"):
                    return {
                        "success": True,
                        "file_id": result["file"]["id"],
                        "file_name": result["file"]["name"],
                        "channel": channel
                    }
                else:
                    raise ConnectionError(f"Slack API error: {result.get('error')}")
                    
            except requests.exceptions.RequestException as e:
                raise ConnectionError(f"Slack upload failed: {e}")
                
    def _get_users(self) -> List[Dict[str, Any]]:
        """Get list of users in workspace"""
        if not self.token:
            raise ComponentError("Slack token not specified")
            
        url = f"{self.api_url}/users.list"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                users = []
                for user in result["members"]:
                    if not user.get("is_bot") and not user.get("deleted"):
                        users.append({
                            "id": user["id"],
                            "name": user.get("name"),
                            "real_name": user.get("real_name"),
                            "email": user.get("profile", {}).get("email")
                        })
                return users
            else:
                raise ConnectionError(f"Slack API error: {result.get('error')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Slack request failed: {e}")
            
    def _get_channels(self) -> List[Dict[str, Any]]:
        """Get list of channels"""
        if not self.token:
            raise ComponentError("Slack token not specified")
            
        url = f"{self.api_url}/conversations.list"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"types": "public_channel,private_channel"}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                channels = []
                for channel in result["channels"]:
                    channels.append({
                        "id": channel["id"],
                        "name": channel["name"],
                        "is_private": channel.get("is_private", False),
                        "num_members": channel.get("num_members", 0)
                    })
                return channels
            else:
                raise ConnectionError(f"Slack API error: {result.get('error')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Slack request failed: {e}")
            
    def _search(self, data: Any) -> Dict[str, Any]:
        """Search messages in Slack"""
        query = data if isinstance(data, str) else data.get('query')
        
        if not query:
            query = self.uri.get_param('query')
            
        if not query:
            raise ComponentError("Search query not specified")
        if not self.token:
            raise ComponentError("Slack token not specified")
            
        url = f"{self.api_url}/search.messages"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"query": query}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                messages = []
                for match in result.get("messages", {}).get("matches", []):
                    messages.append({
                        "text": match.get("text"),
                        "user": match.get("user"),
                        "channel": match.get("channel", {}).get("name"),
                        "ts": match.get("ts")
                    })
                return {"query": query, "count": len(messages), "messages": messages}
            else:
                raise ConnectionError(f"Slack API error: {result.get('error')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Slack search failed: {e}")
            
    def _add_reaction(self, data: Any) -> Dict[str, Any]:
        """Add reaction to a message"""
        if not isinstance(data, dict):
            raise ComponentError("Reaction data must be a dictionary")
            
        channel = data.get('channel')
        timestamp = data.get('timestamp', data.get('ts'))
        emoji = data.get('emoji', 'thumbsup')
        
        if not channel or not timestamp:
            raise ComponentError("Channel and timestamp required for reaction")
        if not self.token:
            raise ComponentError("Slack token not specified")
            
        url = f"{self.api_url}/reactions.add"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": channel,
            "timestamp": timestamp,
            "name": emoji
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                return {
                    "success": True,
                    "channel": channel,
                    "timestamp": timestamp,
                    "emoji": emoji
                }
            else:
                raise ConnectionError(f"Slack API error: {result.get('error')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Slack reaction failed: {e}")
            
    def _create_channel(self, data: Any) -> Dict[str, Any]:
        """Create a new channel"""
        name = data if isinstance(data, str) else data.get('name')
        
        if not name:
            name = self.uri.get_param('name')
            
        if not name:
            raise ComponentError("Channel name not specified")
        if not self.token:
            raise ComponentError("Slack token not specified")
            
        is_private = self.uri.get_param('private', False)
        
        url = f"{self.api_url}/conversations.create"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": name,
            "is_private": is_private
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                return {
                    "success": True,
                    "channel_id": result["channel"]["id"],
                    "channel_name": result["channel"]["name"]
                }
            else:
                raise ConnectionError(f"Slack API error: {result.get('error')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Slack channel creation failed: {e}")


@register("slack-events")
class SlackEventsComponent(StreamComponent):
    """Slack Events API handler"""
    
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.token = uri.get_param('token')
        self.verification_token = uri.get_param('verification_token')
        
    def process(self, data: Any) -> Any:
        """Process Slack event"""
        if not isinstance(data, dict):
            return data
            
        # Handle URL verification challenge
        if data.get("type") == "url_verification":
            return {"challenge": data.get("challenge")}
            
        # Verify token
        if self.verification_token and data.get("token") != self.verification_token:
            raise ComponentError("Invalid verification token")
            
        # Process event
        event = data.get("event", {})
        return {
            "type": event.get("type"),
            "user": event.get("user"),
            "text": event.get("text"),
            "channel": event.get("channel"),
            "ts": event.get("ts")
        }
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream Slack events (requires webhook setup)"""
        logger.info("Slack events require webhook configuration")
        yield {"info": "Configure Slack Events API webhook to receive events"}


@register("slack-slash")
class SlackSlashComponent(Component):
    """Slack slash command handler"""
    
    input_mime = "application/x-www-form-urlencoded"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Process Slack slash command"""
        if not isinstance(data, dict):
            return {"text": "Invalid command data"}
            
        command = data.get("command")
        text = data.get("text", "")
        user_id = data.get("user_id")
        channel_id = data.get("channel_id")
        
        # Return response for Slack
        return {
            "response_type": "in_channel",  # or "ephemeral" for private response
            "text": f"Processing command: {command} {text}",
            "attachments": []
        }
