"""
SMS Component for Streamware - SMS messaging via various providers
"""

import json
import requests
from typing import Any, Optional, Iterator, Dict, List
from ..core import Component, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.debug("Twilio not installed. SMS via Twilio will not be available.")


@register("sms")
class SMSComponent(Component):
    """
    SMS component for sending text messages
    
    Supports multiple providers:
    1. Twilio
    2. Vonage (Nexmo)
    3. Plivo
    4. Generic HTTP SMS gateway
    
    URI formats:
        sms://send?to=+1234567890&provider=twilio
        sms://send?to=+1234567890&provider=vonage&api_key=KEY&api_secret=SECRET
        sms://bulk?provider=twilio&numbers=+123,+456
        sms://verify?to=+1234567890&code=123456
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "send"
        self.provider = uri.get_param('provider', 'twilio')
        
        # Provider configuration
        if self.provider == 'twilio':
            self.account_sid = uri.get_param('account_sid', uri.get_param('twilio_sid'))
            self.auth_token = uri.get_param('auth_token', uri.get_param('twilio_token'))
            self.from_number = uri.get_param('from', uri.get_param('from_number'))
        elif self.provider == 'vonage':
            self.api_key = uri.get_param('api_key')
            self.api_secret = uri.get_param('api_secret')
            self.from_number = uri.get_param('from', 'Streamware')
        elif self.provider == 'plivo':
            self.auth_id = uri.get_param('auth_id')
            self.auth_token = uri.get_param('auth_token')
            self.from_number = uri.get_param('from')
        elif self.provider == 'gateway':
            self.gateway_url = uri.get_param('gateway_url')
            self.api_key = uri.get_param('api_key')
            
    def process(self, data: Any) -> Any:
        """Process SMS operation"""
        if self.operation == "send":
            return self._send_sms(data)
        elif self.operation == "bulk":
            return self._send_bulk(data)
        elif self.operation == "verify":
            return self._send_verification(data)
        elif self.operation == "status":
            return self._check_status(data)
        else:
            raise ComponentError(f"Unknown SMS operation: {self.operation}")
            
    def _send_sms(self, data: Any) -> Dict[str, Any]:
        """Send single SMS message"""
        to = self.uri.get_param('to', self.uri.get_param('phone'))
        
        if isinstance(data, dict):
            to = to or data.get('to', data.get('phone'))
            message = data.get('message', data.get('text', ''))
        else:
            message = str(data) if data else ''
            
        if not to:
            raise ComponentError("Recipient phone number not specified")
        if not message:
            raise ComponentError("Message text not specified")
            
        # Format phone number
        to = self._format_phone(to)
        
        if self.provider == 'twilio':
            return self._send_twilio(to, message)
        elif self.provider == 'vonage':
            return self._send_vonage(to, message)
        elif self.provider == 'plivo':
            return self._send_plivo(to, message)
        elif self.provider == 'gateway':
            return self._send_gateway(to, message)
        else:
            raise ComponentError(f"Unknown SMS provider: {self.provider}")
            
    def _send_twilio(self, to: str, message: str) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        if not TWILIO_AVAILABLE:
            raise ComponentError("Twilio not installed. Install with: pip install twilio")
            
        if not self.account_sid or not self.auth_token:
            raise ComponentError("Twilio credentials not configured")
        if not self.from_number:
            raise ComponentError("From number not specified")
            
        try:
            client = TwilioClient(self.account_sid, self.auth_token)
            
            sms = client.messages.create(
                body=message,
                from_=self.from_number,
                to=to
            )
            
            return {
                "success": True,
                "sid": sms.sid,
                "status": sms.status,
                "to": to,
                "provider": "twilio"
            }
            
        except Exception as e:
            raise ConnectionError(f"Twilio SMS error: {e}")
            
    def _send_vonage(self, to: str, message: str) -> Dict[str, Any]:
        """Send SMS via Vonage (Nexmo)"""
        if not self.api_key or not self.api_secret:
            raise ComponentError("Vonage API credentials not configured")
            
        url = "https://rest.nexmo.com/sms/json"
        
        payload = {
            "from": self.from_number,
            "to": to,
            "text": message,
            "api_key": self.api_key,
            "api_secret": self.api_secret
        }
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            result = response.json()
            
            messages = result.get("messages", [])
            if messages and messages[0].get("status") == "0":
                return {
                    "success": True,
                    "message_id": messages[0].get("message-id"),
                    "to": to,
                    "provider": "vonage"
                }
            else:
                error = messages[0].get("error-text") if messages else "Unknown error"
                raise ConnectionError(f"Vonage SMS error: {error}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Vonage request failed: {e}")
            
    def _send_plivo(self, to: str, message: str) -> Dict[str, Any]:
        """Send SMS via Plivo"""
        if not self.auth_id or not self.auth_token:
            raise ComponentError("Plivo credentials not configured")
        if not self.from_number:
            raise ComponentError("From number not specified")
            
        url = f"https://api.plivo.com/v1/Account/{self.auth_id}/Message/"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "src": self.from_number,
            "dst": to,
            "text": message
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                auth=(self.auth_id, self.auth_token)
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("message"):
                return {
                    "success": True,
                    "message_uuid": result.get("message_uuid", [""])[0],
                    "to": to,
                    "provider": "plivo"
                }
            else:
                raise ConnectionError(f"Plivo SMS error: {result}")
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Plivo request failed: {e}")
            
    def _send_gateway(self, to: str, message: str) -> Dict[str, Any]:
        """Send SMS via generic HTTP gateway"""
        if not self.gateway_url:
            raise ComponentError("Gateway URL not configured")
            
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "to": to,
            "message": message,
            "from": self.from_number
        }
        
        try:
            response = requests.post(self.gateway_url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {
                "success": True,
                "to": to,
                "provider": "gateway"
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"SMS gateway error: {e}")
            
    def _send_bulk(self, data: Any) -> List[Dict[str, Any]]:
        """Send SMS to multiple recipients"""
        numbers = self.uri.get_param('numbers', self.uri.get_param('phones'))
        
        if isinstance(data, dict):
            numbers = numbers or data.get('numbers', data.get('phones', []))
            message = data.get('message', data.get('text', ''))
        else:
            message = str(data) if data else ''
            
        if not numbers:
            raise ComponentError("Phone numbers not specified")
        if not message:
            raise ComponentError("Message text not specified")
            
        # Convert to list if string
        if isinstance(numbers, str):
            numbers = [n.strip() for n in numbers.split(',')]
            
        results = []
        for number in numbers:
            try:
                result = self._send_sms({"to": number, "message": message})
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "to": number,
                    "error": str(e)
                })
                
        return results
        
    def _send_verification(self, data: Any) -> Dict[str, Any]:
        """Send verification code via SMS"""
        to = self.uri.get_param('to', self.uri.get_param('phone'))
        code = self.uri.get_param('code')
        
        if isinstance(data, dict):
            to = to or data.get('to', data.get('phone'))
            code = code or data.get('code')
            
        if not to:
            raise ComponentError("Phone number not specified")
        if not code:
            # Generate random code
            import random
            code = str(random.randint(100000, 999999))
            
        message = f"Your verification code is: {code}"
        
        result = self._send_sms({"to": to, "message": message})
        result["verification_code"] = code
        
        return result
        
    def _check_status(self, data: Any) -> Dict[str, Any]:
        """Check SMS delivery status"""
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
                
        # For other providers, implement their specific status check APIs
        return {"message_id": message_id, "status": "unknown"}
        
    def _format_phone(self, phone: str) -> str:
        """Format phone number to international format"""
        # Remove non-digits except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Add + if not present
        if not cleaned.startswith('+'):
            # Assume US number if 10 digits
            if len(cleaned) == 10:
                cleaned = f"+1{cleaned}"
            else:
                cleaned = f"+{cleaned}"
                
        return cleaned


@register("sms-webhook")
class SMSWebhookComponent(Component):
    """Process SMS webhook events (delivery status, incoming messages)"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Process SMS webhook payload"""
        if not isinstance(data, dict):
            return data
            
        # Detect provider based on payload structure
        if 'MessageSid' in data:
            # Twilio webhook
            return {
                "provider": "twilio",
                "message_sid": data.get('MessageSid'),
                "status": data.get('SmsStatus', data.get('MessageStatus')),
                "from": data.get('From'),
                "to": data.get('To'),
                "body": data.get('Body')
            }
        elif 'msisdn' in data:
            # Vonage webhook
            return {
                "provider": "vonage",
                "message_id": data.get('messageId'),
                "status": data.get('status'),
                "from": data.get('msisdn'),
                "to": data.get('to'),
                "text": data.get('text')
            }
        elif 'MessageUUID' in data:
            # Plivo webhook
            return {
                "provider": "plivo",
                "message_uuid": data.get('MessageUUID'),
                "status": data.get('Status'),
                "from": data.get('From'),
                "to": data.get('To'),
                "text": data.get('Text')
            }
            
        return data
