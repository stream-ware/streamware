"""
Microsoft Teams Component for Streamware - Teams integration
"""

import json
import requests
from typing import Any, Optional, Iterator, Dict, List
from ..core import Component, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)


@register("teams")
@register("msteams")
class TeamsComponent(Component):
    """
    Microsoft Teams component for sending messages via webhooks and Graph API
    
    URI formats:
        teams://webhook?url=https://outlook.office.com/webhook/...
        teams://send?channel=CHANNEL_ID&team=TEAM_ID&token=TOKEN
        teams://card?webhook_url=URL
        teams://mention?user=user@company.com
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "webhook"
        self.webhook_url = uri.get_param('url', uri.get_param('webhook_url'))
        self.token = uri.get_param('token')
        self.graph_url = "https://graph.microsoft.com/v1.0"
        
    def process(self, data: Any) -> Any:
        """Process Teams operation"""
        if self.operation == "webhook":
            return self._send_webhook(data)
        elif self.operation == "card":
            return self._send_card(data)
        elif self.operation == "send":
            return self._send_via_graph(data)
        elif self.operation == "mention":
            return self._send_with_mention(data)
        else:
            raise ComponentError(f"Unknown Teams operation: {self.operation}")
            
    def _send_webhook(self, data: Any) -> Dict[str, Any]:
        """Send message via Teams webhook"""
        if not self.webhook_url:
            raise ComponentError("Webhook URL not specified")
            
        if isinstance(data, dict):
            payload = data
        else:
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "text": str(data) if data else ''
            }
            
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            
            return {
                "success": True,
                "webhook": self.webhook_url[:50] + "..."
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Teams webhook error: {e}")
            
    def _send_card(self, data: Any) -> Dict[str, Any]:
        """Send adaptive card to Teams"""
        if not self.webhook_url:
            raise ComponentError("Webhook URL not specified")
            
        title = self.uri.get_param('title', 'Notification')
        subtitle = self.uri.get_param('subtitle', '')
        
        if isinstance(data, dict):
            title = data.get('title', title)
            subtitle = data.get('subtitle', subtitle)
            text = data.get('text', data.get('message', ''))
            facts = data.get('facts', [])
            actions = data.get('actions', [])
        else:
            text = str(data) if data else ''
            facts = []
            actions = []
            
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": subtitle,
                "text": text,
                "facts": facts
            }],
            "potentialAction": actions
        }
        
        try:
            response = requests.post(self.webhook_url, json=card)
            response.raise_for_status()
            
            return {
                "success": True,
                "card_type": "adaptive",
                "title": title
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Teams card error: {e}")
            
    def _send_via_graph(self, data: Any) -> Dict[str, Any]:
        """Send message via Microsoft Graph API"""
        if not self.token:
            raise ComponentError("Graph API token not specified")
            
        team_id = self.uri.get_param('team', self.uri.get_param('team_id'))
        channel_id = self.uri.get_param('channel', self.uri.get_param('channel_id'))
        
        if isinstance(data, dict):
            team_id = team_id or data.get('team_id')
            channel_id = channel_id or data.get('channel_id')
            content = data.get('content', data.get('message', ''))
        else:
            content = str(data) if data else ''
            
        if not team_id or not channel_id:
            raise ComponentError("Team ID and Channel ID required")
            
        url = f"{self.graph_url}/teams/{team_id}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "body": {
                "content": content,
                "contentType": "html"
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "message_id": result.get("id"),
                "channel_id": channel_id
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Teams Graph API error: {e}")
            
    def _send_with_mention(self, data: Any) -> Dict[str, Any]:
        """Send message with user mention"""
        if not self.webhook_url:
            raise ComponentError("Webhook URL not specified")
            
        user = self.uri.get_param('user')
        
        if isinstance(data, dict):
            user = user or data.get('user')
            text = data.get('text', data.get('message', ''))
        else:
            text = str(data) if data else ''
            
        if not user:
            raise ComponentError("User to mention not specified")
            
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "text": f"<at>{user}</at> {text}"
        }
        
        try:
            response = requests.post(self.webhook_url, json=card)
            response.raise_for_status()
            
            return {
                "success": True,
                "mentioned": user
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Teams mention error: {e}")


@register("signal")
class SignalComponent(Component):
    """
    Signal messenger component using signal-cli
    
    URI formats:
        signal://send?to=+1234567890
        signal://group_send?group_id=GROUP_ID
        signal://receive
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "send"
        self.username = uri.get_param('username', uri.get_param('phone'))
        self.config_path = uri.get_param('config', '~/.local/share/signal-cli')
        
    def process(self, data: Any) -> Any:
        """Process Signal operation"""
        if self.operation == "send":
            return self._send_message(data)
        elif self.operation == "group_send":
            return self._send_group_message(data)
        elif self.operation == "receive":
            return self._receive_messages()
        else:
            raise ComponentError(f"Unknown Signal operation: {self.operation}")
            
    def _send_message(self, data: Any) -> Dict[str, Any]:
        """Send Signal message using signal-cli"""
        import subprocess
        
        to = self.uri.get_param('to')
        
        if isinstance(data, dict):
            to = to or data.get('to', data.get('phone'))
            message = data.get('message', data.get('text', ''))
        else:
            message = str(data) if data else ''
            
        if not to:
            raise ComponentError("Recipient not specified")
        if not self.username:
            raise ComponentError("Signal username not configured")
            
        try:
            cmd = [
                'signal-cli',
                '-u', self.username,
                'send',
                '-m', message,
                to
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "to": to,
                    "message": message[:100]
                }
            else:
                raise ConnectionError(f"signal-cli error: {result.stderr}")
                
        except FileNotFoundError:
            raise ComponentError("signal-cli not installed")
            
    def _send_group_message(self, data: Any) -> Dict[str, Any]:
        """Send message to Signal group"""
        import subprocess
        
        group_id = self.uri.get_param('group_id')
        
        if isinstance(data, dict):
            group_id = group_id or data.get('group_id')
            message = data.get('message', data.get('text', ''))
        else:
            message = str(data) if data else ''
            
        if not group_id:
            raise ComponentError("Group ID not specified")
            
        try:
            cmd = [
                'signal-cli',
                '-u', self.username,
                'send',
                '-m', message,
                '-g', group_id
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "group_id": group_id
                }
            else:
                raise ConnectionError(f"signal-cli error: {result.stderr}")
                
        except FileNotFoundError:
            raise ComponentError("signal-cli not installed")
            
    def _receive_messages(self) -> List[Dict[str, Any]]:
        """Receive Signal messages"""
        import subprocess
        
        try:
            cmd = [
                'signal-cli',
                '-u', self.username,
                'receive',
                '--json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                messages = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        msg = json.loads(line)
                        messages.append({
                            "from": msg.get("envelope", {}).get("source"),
                            "text": msg.get("envelope", {}).get("dataMessage", {}).get("message"),
                            "timestamp": msg.get("envelope", {}).get("timestamp")
                        })
                return messages
            else:
                raise ConnectionError(f"signal-cli error: {result.stderr}")
                
        except FileNotFoundError:
            raise ComponentError("signal-cli not installed")


@register("matrix")
class MatrixComponent(Component):
    """
    Matrix protocol component for decentralized chat
    
    URI formats:
        matrix://send?room_id=!roomid:server&homeserver=https://matrix.org
        matrix://join?room_alias=#room:server
        matrix://create_room?name=MyRoom
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "send"
        self.homeserver = uri.get_param('homeserver', 'https://matrix.org')
        self.access_token = uri.get_param('token', uri.get_param('access_token'))
        self.user_id = uri.get_param('user_id')
        
    def process(self, data: Any) -> Any:
        """Process Matrix operation"""
        if self.operation == "send":
            return self._send_message(data)
        elif self.operation == "join":
            return self._join_room(data)
        elif self.operation == "create_room":
            return self._create_room(data)
        else:
            raise ComponentError(f"Unknown Matrix operation: {self.operation}")
            
    def _send_message(self, data: Any) -> Dict[str, Any]:
        """Send message to Matrix room"""
        room_id = self.uri.get_param('room_id', self.uri.get_param('room'))
        
        if isinstance(data, dict):
            room_id = room_id or data.get('room_id')
            content = data.get('content', data.get('message', ''))
            msgtype = data.get('msgtype', 'm.text')
        else:
            content = str(data) if data else ''
            msgtype = 'm.text'
            
        if not room_id:
            raise ComponentError("Room ID not specified")
        if not self.access_token:
            raise ComponentError("Access token not specified")
            
        import time
        txn_id = str(int(time.time() * 1000))
        
        url = f"{self.homeserver}/_matrix/client/r0/rooms/{room_id}/send/m.room.message/{txn_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "msgtype": msgtype,
            "body": content
        }
        
        try:
            response = requests.put(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "event_id": result.get("event_id"),
                "room_id": room_id
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Matrix API error: {e}")
            
    def _join_room(self, data: Any) -> Dict[str, Any]:
        """Join a Matrix room"""
        room_alias = data if isinstance(data, str) else data.get('room_alias')
        
        if not room_alias:
            room_alias = self.uri.get_param('room_alias')
            
        if not room_alias:
            raise ComponentError("Room alias not specified")
            
        url = f"{self.homeserver}/_matrix/client/r0/join/{room_alias}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "room_id": result.get("room_id")
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Matrix join error: {e}")
            
    def _create_room(self, data: Any) -> Dict[str, Any]:
        """Create a Matrix room"""
        if isinstance(data, dict):
            name = data.get('name')
            topic = data.get('topic', '')
            invite = data.get('invite', [])
        else:
            name = self.uri.get_param('name', 'New Room')
            topic = self.uri.get_param('topic', '')
            invite = []
            
        url = f"{self.homeserver}/_matrix/client/r0/createRoom"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": name,
            "topic": topic,
            "invite": invite
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "room_id": result.get("room_id"),
                "room_alias": result.get("room_alias")
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Matrix room creation error: {e}")
