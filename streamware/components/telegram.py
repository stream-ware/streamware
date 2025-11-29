"""
Telegram Component for Streamware - Telegram Bot API integration
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
    import telegram
    from telegram import Bot, Update
    from telegram.ext import Updater
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.debug("python-telegram-bot not installed. Using HTTP API fallback.")


@register("telegram")
@register("tg")
class TelegramComponent(Component):
    """
    Telegram component for sending and receiving messages
    
    URI formats:
        telegram://send?chat_id=@channel&token=BOT_TOKEN
        telegram://send_photo?chat_id=USER_ID&photo=path/to/photo.jpg
        telegram://poll?token=BOT_TOKEN&timeout=30
        telegram://webhook?token=BOT_TOKEN&url=https://myapp.com/telegram
        telegram://command?token=BOT_TOKEN&command=/start
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "send"
        self.token = uri.get_param('token', uri.get_param('bot_token'))
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        
        if not self.token:
            raise ComponentError("Telegram bot token not specified")
            
    def process(self, data: Any) -> Any:
        """Process Telegram operation"""
        if self.operation == "send":
            return self._send_message(data)
        elif self.operation == "send_photo":
            return self._send_photo(data)
        elif self.operation == "send_document":
            return self._send_document(data)
        elif self.operation == "send_location":
            return self._send_location(data)
        elif self.operation == "poll":
            return self._poll_updates()
        elif self.operation == "get_updates":
            return self._get_updates()
        elif self.operation == "webhook":
            return self._set_webhook(data)
        elif self.operation == "get_chat":
            return self._get_chat(data)
        elif self.operation == "get_file":
            return self._get_file(data)
        else:
            raise ComponentError(f"Unknown Telegram operation: {self.operation}")
            
    def _send_message(self, data: Any) -> Dict[str, Any]:
        """Send text message via Telegram"""
        chat_id = self.uri.get_param('chat_id')
        parse_mode = self.uri.get_param('parse_mode', 'HTML')
        disable_notification = self.uri.get_param('silent', False)
        reply_to = self.uri.get_param('reply_to')
        
        # Get parameters from data if not in URI
        if isinstance(data, dict):
            chat_id = chat_id or data.get('chat_id')
            text = data.get('text', data.get('message', ''))
            parse_mode = data.get('parse_mode', parse_mode)
            reply_to = data.get('reply_to', reply_to)
        else:
            text = str(data) if data else ''
            
        if not chat_id:
            raise ComponentError("Chat ID not specified")
            
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_notification': disable_notification
        }
        
        if reply_to:
            payload['reply_to_message_id'] = reply_to
            
        try:
            response = requests.post(f"{self.api_url}/sendMessage", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result['result']
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to send Telegram message: {e}")
            
    def _send_photo(self, data: Any) -> Dict[str, Any]:
        """Send photo via Telegram"""
        chat_id = self.uri.get_param('chat_id')
        caption = self.uri.get_param('caption', '')
        
        if isinstance(data, dict):
            chat_id = chat_id or data.get('chat_id')
            photo = data.get('photo')
            caption = data.get('caption', caption)
        else:
            photo = self.uri.get_param('photo')
            
        if not chat_id:
            raise ComponentError("Chat ID not specified")
        if not photo:
            raise ComponentError("Photo path or URL not specified")
            
        try:
            # Check if photo is URL or file path
            if photo.startswith(('http://', 'https://')):
                # Send by URL
                payload = {
                    'chat_id': chat_id,
                    'photo': photo,
                    'caption': caption
                }
                response = requests.post(f"{self.api_url}/sendPhoto", json=payload)
            else:
                # Send by file
                from pathlib import Path
                photo_path = Path(photo)
                if not photo_path.exists():
                    raise ComponentError(f"Photo file not found: {photo}")
                    
                with open(photo_path, 'rb') as f:
                    files = {'photo': f}
                    data = {
                        'chat_id': chat_id,
                        'caption': caption
                    }
                    response = requests.post(f"{self.api_url}/sendPhoto", data=data, files=files)
                    
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result['result']
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to send photo: {e}")
            
    def _send_document(self, data: Any) -> Dict[str, Any]:
        """Send document via Telegram"""
        chat_id = self.uri.get_param('chat_id')
        caption = self.uri.get_param('caption', '')
        
        if isinstance(data, dict):
            chat_id = chat_id or data.get('chat_id')
            document = data.get('document')
            caption = data.get('caption', caption)
        else:
            document = self.uri.get_param('document')
            
        if not chat_id:
            raise ComponentError("Chat ID not specified")
        if not document:
            raise ComponentError("Document path not specified")
            
        try:
            from pathlib import Path
            doc_path = Path(document)
            
            if not doc_path.exists():
                raise ComponentError(f"Document not found: {document}")
                
            with open(doc_path, 'rb') as f:
                files = {'document': f}
                data = {
                    'chat_id': chat_id,
                    'caption': caption
                }
                response = requests.post(f"{self.api_url}/sendDocument", data=data, files=files)
                
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result['result']
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to send document: {e}")
            
    def _send_location(self, data: Any) -> Dict[str, Any]:
        """Send location via Telegram"""
        chat_id = self.uri.get_param('chat_id')
        
        if isinstance(data, dict):
            chat_id = chat_id or data.get('chat_id')
            latitude = data.get('latitude', data.get('lat'))
            longitude = data.get('longitude', data.get('lon', data.get('lng')))
        else:
            latitude = self.uri.get_param('latitude', self.uri.get_param('lat'))
            longitude = self.uri.get_param('longitude', self.uri.get_param('lon'))
            
        if not chat_id:
            raise ComponentError("Chat ID not specified")
        if not latitude or not longitude:
            raise ComponentError("Location coordinates not specified")
            
        payload = {
            'chat_id': chat_id,
            'latitude': float(latitude),
            'longitude': float(longitude)
        }
        
        try:
            response = requests.post(f"{self.api_url}/sendLocation", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result['result']
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to send location: {e}")
            
    def _poll_updates(self) -> List[Dict[str, Any]]:
        """Poll for updates (long polling)"""
        timeout = self.uri.get_param('timeout', 30)
        offset = self.uri.get_param('offset', 0)
        
        payload = {
            'timeout': timeout,
            'offset': offset
        }
        
        try:
            response = requests.post(f"{self.api_url}/getUpdates", json=payload, timeout=timeout+5)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result['result']
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to poll updates: {e}")
            
    def _get_updates(self) -> List[Dict[str, Any]]:
        """Get recent updates"""
        limit = self.uri.get_param('limit', 100)
        offset = self.uri.get_param('offset', 0)
        
        payload = {
            'limit': limit,
            'offset': offset
        }
        
        try:
            response = requests.post(f"{self.api_url}/getUpdates", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result['result']
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to get updates: {e}")
            
    def _set_webhook(self, data: Any) -> Dict[str, Any]:
        """Set webhook for updates"""
        if isinstance(data, dict):
            url = data.get('url')
        else:
            url = str(data) if data else self.uri.get_param('url')
            
        if not url:
            raise ComponentError("Webhook URL not specified")
            
        payload = {'url': url}
        
        try:
            response = requests.post(f"{self.api_url}/setWebhook", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return {"success": True, "webhook": url}
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to set webhook: {e}")
            
    def _get_chat(self, data: Any) -> Dict[str, Any]:
        """Get chat information"""
        chat_id = data if isinstance(data, (str, int)) else data.get('chat_id')
        
        if not chat_id:
            chat_id = self.uri.get_param('chat_id')
            
        if not chat_id:
            raise ComponentError("Chat ID not specified")
            
        payload = {'chat_id': chat_id}
        
        try:
            response = requests.post(f"{self.api_url}/getChat", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result['result']
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to get chat: {e}")
            
    def _get_file(self, data: Any) -> Dict[str, Any]:
        """Get file information"""
        file_id = data if isinstance(data, str) else data.get('file_id')
        
        if not file_id:
            raise ComponentError("File ID not specified")
            
        payload = {'file_id': file_id}
        
        try:
            response = requests.post(f"{self.api_url}/getFile", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                file_info = result['result']
                # Add download URL
                file_info['download_url'] = f"https://api.telegram.org/file/bot{self.token}/{file_info['file_path']}"
                return file_info
            else:
                raise ConnectionError(f"Telegram API error: {result.get('description')}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to get file: {e}")


@register("telegram-bot")
class TelegramBotComponent(StreamComponent):
    """Telegram bot component for receiving messages"""
    
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.telegram = TelegramComponent(uri)
        self.offset = 0
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream incoming Telegram messages"""
        logger.info("Starting Telegram bot listener")
        
        while True:
            try:
                updates = self.telegram._poll_updates()
                
                for update in updates:
                    # Update offset to avoid getting same updates
                    self.offset = max(self.offset, update['update_id'] + 1)
                    self.telegram.uri.update_param('offset', self.offset)
                    
                    yield update
                    
            except Exception as e:
                logger.error(f"Error polling Telegram: {e}")
                time.sleep(5)  # Wait before retrying
                
    def process(self, data: Any) -> Any:
        """Get current updates"""
        return self.telegram._get_updates()


@register("telegram-command")
class TelegramCommandComponent(Component):
    """Process Telegram bot commands"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Process Telegram update for commands"""
        if not isinstance(data, dict):
            return data
            
        # Extract message
        message = data.get('message', {})
        text = message.get('text', '')
        
        # Check if it's a command
        if text.startswith('/'):
            command_parts = text.split()
            command = command_parts[0]
            args = command_parts[1:] if len(command_parts) > 1 else []
            
            return {
                "is_command": True,
                "command": command,
                "args": args,
                "chat_id": message.get('chat', {}).get('id'),
                "user": message.get('from', {}),
                "message_id": message.get('message_id'),
                "original": data
            }
            
        return {
            "is_command": False,
            "text": text,
            "chat_id": message.get('chat', {}).get('id'),
            "user": message.get('from', {}),
            "message_id": message.get('message_id'),
            "original": data
        }
