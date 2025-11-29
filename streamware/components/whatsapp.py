"""
WhatsApp Component for Streamware - WhatsApp Business API integration
"""

import json
import requests
from typing import Any, Optional, Iterator, Dict, List
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.debug("Twilio not installed. WhatsApp via Twilio will not be available.")


@register("whatsapp")
@register("wa")
class WhatsAppComponent(Component):
    """
    WhatsApp component for sending messages
    
    Supports multiple providers:
    1. WhatsApp Business API (official)
    2. Twilio WhatsApp
    3. WhatsApp Web automation (via playwright)
    
    URI formats:
        whatsapp://send?phone=+1234567890&provider=twilio
        whatsapp://send?phone=+1234567890&api_url=https://api.whatsapp.com
        whatsapp://broadcast?phones=+123,+456&message=Hello
        whatsapp://template?phone=+123&template=order_confirmation
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "send"
        self.provider = uri.get_param('provider', 'business_api')
        
        # Provider configuration
        if self.provider == 'twilio':
            self.account_sid = uri.get_param('account_sid', uri.get_param('twilio_sid'))
            self.auth_token = uri.get_param('auth_token', uri.get_param('twilio_token'))
            self.from_number = uri.get_param('from', uri.get_param('from_number'))
        elif self.provider == 'business_api':
            self.api_url = uri.get_param('api_url', 'https://graph.facebook.com/v17.0')
            self.access_token = uri.get_param('token', uri.get_param('access_token'))
            self.phone_number_id = uri.get_param('phone_number_id')
        elif self.provider == 'web':
            self.session = uri.get_param('session', 'whatsapp_session')
            
    def process(self, data: Any) -> Any:
        """Process WhatsApp operation"""
        if self.operation == "send":
            return self._send_message(data)
        elif self.operation == "send_media":
            return self._send_media(data)
        elif self.operation == "broadcast":
            return self._broadcast_message(data)
        elif self.operation == "template":
            return self._send_template(data)
        elif self.operation == "status":
            return self._check_status(data)
        else:
            raise ComponentError(f"Unknown WhatsApp operation: {self.operation}")
            
    def _send_message(self, data: Any) -> Dict[str, Any]:
        """Send WhatsApp message"""
        phone = self.uri.get_param('phone', self.uri.get_param('to'))
        
        if isinstance(data, dict):
            phone = phone or data.get('phone', data.get('to'))
            message = data.get('message', data.get('text', ''))
        else:
            message = str(data) if data else ''
            
        if not phone:
            raise ComponentError("Phone number not specified")
            
        # Format phone number
        phone = self._format_phone(phone)
        
        if self.provider == 'twilio':
            return self._send_via_twilio(phone, message)
        elif self.provider == 'business_api':
            return self._send_via_business_api(phone, message)
        elif self.provider == 'web':
            return self._send_via_web(phone, message)
        else:
            raise ComponentError(f"Unknown provider: {self.provider}")
            
    def _send_via_twilio(self, phone: str, message: str) -> Dict[str, Any]:
        """Send message via Twilio WhatsApp"""
        if not TWILIO_AVAILABLE:
            raise ComponentError("Twilio not installed. Install with: pip install twilio")
            
        try:
            client = TwilioClient(self.account_sid, self.auth_token)
            
            # Format WhatsApp number for Twilio
            to_number = f"whatsapp:{phone}"
            from_number = f"whatsapp:{self.from_number}"
            
            message = client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            return {
                "success": True,
                "sid": message.sid,
                "status": message.status,
                "to": phone
            }
            
        except Exception as e:
            raise ConnectionError(f"Twilio WhatsApp error: {e}")
            
    def _send_via_business_api(self, phone: str, message: str) -> Dict[str, Any]:
        """Send message via WhatsApp Business API"""
        if not self.access_token or not self.phone_number_id:
            raise ComponentError("WhatsApp Business API credentials not configured")
            
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "to": phone
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"WhatsApp Business API error: {e}")
            
    def _send_via_web(self, phone: str, message: str) -> Dict[str, Any]:
        """Send message via WhatsApp Web automation"""
        # This would use playwright or selenium to automate WhatsApp Web
        # For now, returning a placeholder
        logger.warning("WhatsApp Web automation not yet implemented")
        return {
            "success": False,
            "error": "WhatsApp Web automation not yet implemented"
        }
        
    def _send_media(self, data: Any) -> Dict[str, Any]:
        """Send media file via WhatsApp"""
        phone = self.uri.get_param('phone', self.uri.get_param('to'))
        media_type = self.uri.get_param('type', 'image')
        
        if isinstance(data, dict):
            phone = phone or data.get('phone', data.get('to'))
            media_url = data.get('media_url', data.get('url'))
            caption = data.get('caption', '')
            media_type = data.get('type', media_type)
        else:
            media_url = self.uri.get_param('media_url', self.uri.get_param('url'))
            caption = self.uri.get_param('caption', '')
            
        if not phone:
            raise ComponentError("Phone number not specified")
        if not media_url:
            raise ComponentError("Media URL not specified")
            
        phone = self._format_phone(phone)
        
        if self.provider == 'business_api':
            return self._send_media_business_api(phone, media_url, media_type, caption)
        elif self.provider == 'twilio':
            return self._send_media_twilio(phone, media_url, caption)
        else:
            raise ComponentError(f"Media sending not supported for provider: {self.provider}")
            
    def _send_media_business_api(self, phone: str, media_url: str, media_type: str, caption: str) -> Dict[str, Any]:
        """Send media via WhatsApp Business API"""
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": media_type,
            media_type: {
                "link": media_url
            }
        }
        
        if caption:
            payload[media_type]["caption"] = caption
            
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "to": phone,
                "media_type": media_type
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"WhatsApp Business API error: {e}")
            
    def _send_media_twilio(self, phone: str, media_url: str, caption: str) -> Dict[str, Any]:
        """Send media via Twilio WhatsApp"""
        if not TWILIO_AVAILABLE:
            raise ComponentError("Twilio not installed")
            
        try:
            client = TwilioClient(self.account_sid, self.auth_token)
            
            to_number = f"whatsapp:{phone}"
            from_number = f"whatsapp:{self.from_number}"
            
            message = client.messages.create(
                body=caption if caption else "Media message",
                media_url=[media_url],
                from_=from_number,
                to=to_number
            )
            
            return {
                "success": True,
                "sid": message.sid,
                "status": message.status,
                "to": phone
            }
            
        except Exception as e:
            raise ConnectionError(f"Twilio WhatsApp error: {e}")
            
    def _broadcast_message(self, data: Any) -> List[Dict[str, Any]]:
        """Broadcast message to multiple recipients"""
        phones = self.uri.get_param('phones')
        
        if isinstance(data, dict):
            phones = phones or data.get('phones', [])
            message = data.get('message', data.get('text', ''))
        else:
            message = str(data) if data else ''
            
        if not phones:
            raise ComponentError("Phone numbers not specified")
            
        # Convert to list if string
        if isinstance(phones, str):
            phones = [p.strip() for p in phones.split(',')]
            
        results = []
        for phone in phones:
            try:
                result = self._send_message({"phone": phone, "message": message})
                results.append(result)
            except Exception as e:
                results.append({"phone": phone, "error": str(e)})
                
        return results
        
    def _send_template(self, data: Any) -> Dict[str, Any]:
        """Send WhatsApp template message"""
        phone = self.uri.get_param('phone', self.uri.get_param('to'))
        template_name = self.uri.get_param('template')
        language = self.uri.get_param('language', 'en')
        
        if isinstance(data, dict):
            phone = phone or data.get('phone', data.get('to'))
            template_name = template_name or data.get('template')
            language = data.get('language', language)
            parameters = data.get('parameters', [])
        else:
            parameters = []
            
        if not phone:
            raise ComponentError("Phone number not specified")
        if not template_name:
            raise ComponentError("Template name not specified")
            
        phone = self._format_phone(phone)
        
        if self.provider == 'business_api':
            url = f"{self.api_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language
                    }
                }
            }
            
            if parameters:
                payload["template"]["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(p)} for p in parameters]
                }]
                
            try:
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "message_id": result.get("messages", [{}])[0].get("id"),
                    "to": phone,
                    "template": template_name
                }
                
            except requests.exceptions.RequestException as e:
                raise ConnectionError(f"WhatsApp template error: {e}")
        else:
            raise ComponentError(f"Template messages not supported for provider: {self.provider}")
            
    def _check_status(self, data: Any) -> Dict[str, Any]:
        """Check message status"""
        message_id = data if isinstance(data, str) else data.get('message_id')
        
        if not message_id:
            raise ComponentError("Message ID not specified")
            
        if self.provider == 'twilio':
            if not TWILIO_AVAILABLE:
                raise ComponentError("Twilio not installed")
                
            try:
                client = TwilioClient(self.account_sid, self.auth_token)
                message = client.messages(message_id).fetch()
                
                return {
                    "message_id": message.sid,
                    "status": message.status,
                    "date_sent": str(message.date_sent),
                    "to": message.to
                }
                
            except Exception as e:
                raise ConnectionError(f"Twilio status check error: {e}")
        else:
            # For Business API, you would implement webhook handling
            return {"message_id": message_id, "status": "unknown"}
            
    def _format_phone(self, phone: str) -> str:
        """Format phone number to international format"""
        # Remove non-digits
        phone = ''.join(filter(str.isdigit, phone))
        
        # Add country code if missing
        if not phone.startswith('+'):
            if len(phone) == 10:  # US number without country code
                phone = f"+1{phone}"
            else:
                phone = f"+{phone}"
                
        return phone


@register("whatsapp-webhook")
class WhatsAppWebhookComponent(Component):
    """Process WhatsApp webhook events"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Process WhatsApp webhook payload"""
        if not isinstance(data, dict):
            return data
            
        # Process different webhook types
        if 'entry' in data:
            # Facebook Graph API webhook format
            entries = data.get('entry', [])
            messages = []
            
            for entry in entries:
                changes = entry.get('changes', [])
                for change in changes:
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        messages.extend(value.get('messages', []))
                        
            return {"messages": messages}
            
        elif 'SmsStatus' in data:
            # Twilio webhook format
            return {
                "message_sid": data.get('MessageSid'),
                "status": data.get('SmsStatus'),
                "from": data.get('From'),
                "to": data.get('To')
            }
            
        return data
