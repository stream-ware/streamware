"""
Discord Component for Streamware - Discord bot integration
"""

import json
import requests
from typing import Any, Optional, Iterator, Dict, List
import asyncio
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)

try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    logger.debug("discord.py not installed. Discord features will be limited.")


@register("discord")
class DiscordComponent(Component):
    """
    Discord component for sending messages and bot operations
    
    URI formats:
        discord://send?channel_id=123456&token=BOT_TOKEN
        discord://send_embed?channel_id=123456&title=Title&description=Desc
        discord://webhook?url=https://discord.com/api/webhooks/...
        discord://get_channel?channel_id=123456
        discord://create_thread?channel_id=123456&name=ThreadName
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "send"
        self.token = uri.get_param('token', uri.get_param('bot_token'))
        self.api_url = "https://discord.com/api/v10"
        
    def process(self, data: Any) -> Any:
        """Process Discord operation"""
        if self.operation == "send":
            return self._send_message(data)
        elif self.operation == "send_embed":
            return self._send_embed(data)
        elif self.operation == "webhook":
            return self._send_webhook(data)
        elif self.operation == "get_channel":
            return self._get_channel(data)
        elif self.operation == "get_guild":
            return self._get_guild(data)
        elif self.operation == "create_thread":
            return self._create_thread(data)
        elif self.operation == "add_reaction":
            return self._add_reaction(data)
        else:
            raise ComponentError(f"Unknown Discord operation: {self.operation}")
            
    def _send_message(self, data: Any) -> Dict[str, Any]:
        """Send message to Discord channel"""
        channel_id = self.uri.get_param('channel_id')
        
        if isinstance(data, dict):
            channel_id = channel_id or data.get('channel_id', data.get('channel'))
            content = data.get('content', data.get('message', data.get('text', '')))
            tts = data.get('tts', False)
        else:
            content = str(data) if data else ''
            tts = False
            
        if not channel_id:
            raise ComponentError("Channel ID not specified")
        if not self.token:
            raise ComponentError("Discord bot token not specified")
            
        url = f"{self.api_url}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "content": content,
            "tts": tts
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Discord API error: {e}")
            
    def _send_embed(self, data: Any) -> Dict[str, Any]:
        """Send embedded message to Discord"""
        channel_id = self.uri.get_param('channel_id')
        title = self.uri.get_param('title', 'Embed')
        description = self.uri.get_param('description', '')
        color = self.uri.get_param('color', 0x00ff00)
        
        if isinstance(data, dict):
            channel_id = channel_id or data.get('channel_id', data.get('channel'))
            title = data.get('title', title)
            description = data.get('description', description)
            color = data.get('color', color)
            fields = data.get('fields', [])
            footer = data.get('footer')
            thumbnail = data.get('thumbnail')
            image = data.get('image')
        else:
            fields = []
            footer = None
            thumbnail = None
            image = None
            
        if not channel_id:
            raise ComponentError("Channel ID not specified")
        if not self.token:
            raise ComponentError("Discord bot token not specified")
            
        url = f"{self.api_url}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }
        
        embed = {
            "title": title,
            "description": description,
            "color": color
        }
        
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer} if isinstance(footer, str) else footer
        if thumbnail:
            embed["thumbnail"] = {"url": thumbnail} if isinstance(thumbnail, str) else thumbnail
        if image:
            embed["image"] = {"url": image} if isinstance(image, str) else image
            
        payload = {"embeds": [embed]}
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Discord API error: {e}")
            
    def _send_webhook(self, data: Any) -> Dict[str, Any]:
        """Send message via Discord webhook"""
        webhook_url = self.uri.get_param('url', self.uri.get_param('webhook_url'))
        username = self.uri.get_param('username', 'Streamware')
        avatar_url = self.uri.get_param('avatar_url')
        
        if isinstance(data, dict):
            webhook_url = webhook_url or data.get('webhook_url', data.get('url'))
            content = data.get('content', data.get('message', data.get('text', '')))
            username = data.get('username', username)
            avatar_url = data.get('avatar_url', avatar_url)
            embeds = data.get('embeds')
        else:
            content = str(data) if data else ''
            embeds = None
            
        if not webhook_url:
            raise ComponentError("Webhook URL not specified")
            
        payload = {
            "content": content,
            "username": username
        }
        
        if avatar_url:
            payload["avatar_url"] = avatar_url
        if embeds:
            payload["embeds"] = embeds
            
        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            
            return {
                "success": True,
                "webhook": webhook_url,
                "message": content[:100] + "..." if len(content) > 100 else content
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Discord webhook error: {e}")
            
    def _get_channel(self, data: Any) -> Dict[str, Any]:
        """Get channel information"""
        channel_id = data if isinstance(data, (str, int)) else data.get('channel_id')
        
        if not channel_id:
            channel_id = self.uri.get_param('channel_id')
            
        if not channel_id:
            raise ComponentError("Channel ID not specified")
        if not self.token:
            raise ComponentError("Discord bot token not specified")
            
        url = f"{self.api_url}/channels/{channel_id}"
        headers = {"Authorization": f"Bot {self.token}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Discord API error: {e}")
            
    def _get_guild(self, data: Any) -> Dict[str, Any]:
        """Get guild (server) information"""
        guild_id = data if isinstance(data, (str, int)) else data.get('guild_id')
        
        if not guild_id:
            guild_id = self.uri.get_param('guild_id', self.uri.get_param('server_id'))
            
        if not guild_id:
            raise ComponentError("Guild ID not specified")
        if not self.token:
            raise ComponentError("Discord bot token not specified")
            
        url = f"{self.api_url}/guilds/{guild_id}"
        headers = {"Authorization": f"Bot {self.token}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Discord API error: {e}")
            
    def _create_thread(self, data: Any) -> Dict[str, Any]:
        """Create a thread in a channel"""
        channel_id = self.uri.get_param('channel_id')
        name = self.uri.get_param('name', 'New Thread')
        
        if isinstance(data, dict):
            channel_id = channel_id or data.get('channel_id')
            name = data.get('name', name)
            auto_archive_duration = data.get('auto_archive_duration', 60)
        else:
            auto_archive_duration = 60
            
        if not channel_id:
            raise ComponentError("Channel ID not specified")
        if not self.token:
            raise ComponentError("Discord bot token not specified")
            
        url = f"{self.api_url}/channels/{channel_id}/threads"
        headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": name,
            "auto_archive_duration": auto_archive_duration,
            "type": 11  # Public thread
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Discord API error: {e}")
            
    def _add_reaction(self, data: Any) -> Dict[str, Any]:
        """Add reaction to a message"""
        if not isinstance(data, dict):
            raise ComponentError("Reaction data must be a dictionary")
            
        channel_id = data.get('channel_id')
        message_id = data.get('message_id')
        emoji = data.get('emoji', '👍')
        
        if not channel_id or not message_id:
            raise ComponentError("Channel ID and Message ID required for reaction")
        if not self.token:
            raise ComponentError("Discord bot token not specified")
            
        # URL encode emoji
        import urllib.parse
        emoji_encoded = urllib.parse.quote(emoji)
        
        url = f"{self.api_url}/channels/{channel_id}/messages/{message_id}/reactions/{emoji_encoded}/@me"
        headers = {"Authorization": f"Bot {self.token}"}
        
        try:
            response = requests.put(url, headers=headers)
            response.raise_for_status()
            
            return {
                "success": True,
                "channel_id": channel_id,
                "message_id": message_id,
                "emoji": emoji
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Discord API error: {e}")


@register("discord-bot")
class DiscordBotComponent(StreamComponent):
    """Discord bot component for receiving events"""
    
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.token = uri.get_param('token', uri.get_param('bot_token'))
        self.intents = uri.get_param('intents', 'default')
        
        if not self.token:
            raise ComponentError("Discord bot token not specified")
            
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream Discord events"""
        if not DISCORD_AVAILABLE:
            raise ComponentError("discord.py not installed. Install with: pip install discord.py")
            
        # This is a simplified implementation
        # In production, you'd set up a proper Discord bot with event listeners
        logger.warning("Discord bot streaming requires async implementation")
        yield {"info": "Discord bot streaming requires full async implementation"}
        
    def process(self, data: Any) -> Any:
        """Process Discord bot commands"""
        return {"info": "Discord bot requires full implementation with discord.py"}


@register("discord-slash")
class DiscordSlashComponent(Component):
    """Discord slash command handler"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Process Discord slash command interaction"""
        if not isinstance(data, dict):
            return data
            
        # Parse Discord interaction
        interaction_type = data.get('type')
        
        if interaction_type == 1:
            # Ping
            return {"type": 1}
        elif interaction_type == 2:
            # Application command
            command_data = data.get('data', {})
            command_name = command_data.get('name')
            options = command_data.get('options', [])
            
            return {
                "type": 4,  # Channel message with source
                "data": {
                    "content": f"Processing command: {command_name}",
                    "embeds": [],
                    "flags": 0
                }
            }
            
        return data
