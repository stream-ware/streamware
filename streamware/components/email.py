"""
Email Component for Streamware - SMTP/IMAP email operations
"""

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Optional, Iterator, Dict, List
from pathlib import Path
import time
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)


@register("email")
@register("smtp")
@register("imap")
class EmailComponent(Component):
    """
    Email component for sending and receiving emails
    
    URI formats:
        email://send?to=user@example.com&subject=Test
        smtp://send?host=smtp.gmail.com&port=587&user=me@gmail.com
        imap://read?host=imap.gmail.com&folder=INBOX&unread=true
        email://watch?host=imap.gmail.com&folder=INBOX&interval=60
    """
    
    input_mime = "text/plain"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "send"
        
        # Email server configuration
        self.smtp_host = uri.get_param('smtp_host', uri.get_param('host', 'localhost'))
        self.smtp_port = uri.get_param('smtp_port', uri.get_param('port', 587))
        self.imap_host = uri.get_param('imap_host', uri.get_param('host', 'localhost'))
        self.imap_port = uri.get_param('imap_port', 993)
        
        # Authentication
        self.user = uri.get_param('user', uri.get_param('username', uri.get_param('email')))
        self.password = uri.get_param('password', uri.get_param('pass'))
        
        # TLS/SSL
        self.use_tls = uri.get_param('tls', True)
        self.use_ssl = uri.get_param('ssl', False)
        
    def process(self, data: Any) -> Any:
        """Process email operation"""
        if self.operation == "send":
            return self._send_email(data)
        elif self.operation == "read":
            return self._read_emails()
        elif self.operation == "delete":
            return self._delete_email(data)
        elif self.operation == "watch":
            return self._watch_inbox()
        elif self.operation == "search":
            return self._search_emails(data)
        else:
            raise ComponentError(f"Unknown email operation: {self.operation}")
            
    def _send_email(self, data: Any) -> Dict[str, Any]:
        """Send an email via SMTP"""
        # Get email parameters
        to = self.uri.get_param('to')
        cc = self.uri.get_param('cc')
        bcc = self.uri.get_param('bcc')
        subject = self.uri.get_param('subject', 'No Subject')
        from_addr = self.uri.get_param('from', self.user)
        
        # Get content from data or params
        if isinstance(data, dict):
            to = to or data.get('to')
            cc = cc or data.get('cc')
            bcc = bcc or data.get('bcc')
            subject = data.get('subject', subject)
            from_addr = data.get('from', from_addr)
            body = data.get('body', data.get('content', ''))
            attachments = data.get('attachments', [])
            html = data.get('html')
        else:
            body = str(data) if data else ''
            attachments = []
            html = None
            
        if not to:
            raise ComponentError("Recipient email address not specified")
            
        try:
            # Create message
            msg = MIMEMultipart() if attachments or html else MIMEText(body)
            
            if isinstance(msg, MIMEMultipart):
                # Add text part
                msg.attach(MIMEText(body, 'plain'))
                
                # Add HTML part if provided
                if html:
                    msg.attach(MIMEText(html, 'html'))
                    
                # Add attachments
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
                    
            msg['From'] = from_addr
            msg['To'] = to if isinstance(to, str) else ', '.join(to)
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = cc if isinstance(cc, str) else ', '.join(cc)
            if bcc:
                msg['Bcc'] = bcc if isinstance(bcc, str) else ', '.join(bcc)
                
            # Connect to SMTP server
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                if self.use_tls:
                    server.starttls()
                    
            # Login if credentials provided
            if self.user and self.password:
                server.login(self.user, self.password)
                
            # Send email
            recipients = [to] if isinstance(to, str) else to
            if cc:
                recipients.extend([cc] if isinstance(cc, str) else cc)
            if bcc:
                recipients.extend([bcc] if isinstance(bcc, str) else bcc)
                
            server.send_message(msg)
            server.quit()
            
            return {
                "success": True,
                "to": to,
                "subject": subject,
                "timestamp": time.time()
            }
            
        except Exception as e:
            raise ConnectionError(f"Failed to send email: {e}")
            
    def _read_emails(self) -> List[Dict[str, Any]]:
        """Read emails from IMAP server"""
        folder = self.uri.get_param('folder', 'INBOX')
        unread_only = self.uri.get_param('unread', False)
        limit = self.uri.get_param('limit', 10)
        
        try:
            # Connect to IMAP server
            if self.use_ssl:
                mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                mail = imaplib.IMAP4(self.imap_host, self.imap_port)
                
            # Login
            if self.user and self.password:
                mail.login(self.user, self.password)
                
            # Select folder
            mail.select(folder)
            
            # Search for emails
            if unread_only:
                typ, data = mail.search(None, 'UNSEEN')
            else:
                typ, data = mail.search(None, 'ALL')
                
            email_ids = data[0].split()
            emails = []
            
            # Get emails (most recent first)
            for email_id in reversed(email_ids[-limit:]):
                typ, msg_data = mail.fetch(email_id, '(RFC822)')
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Extract email data
                        email_dict = {
                            "id": email_id.decode(),
                            "from": msg['From'],
                            "to": msg['To'],
                            "subject": msg['Subject'],
                            "date": msg['Date'],
                            "body": self._get_email_body(msg),
                            "attachments": self._get_attachments(msg)
                        }
                        emails.append(email_dict)
                        
            mail.close()
            mail.logout()
            
            return emails
            
        except Exception as e:
            raise ConnectionError(f"Failed to read emails: {e}")
            
    def _delete_email(self, data: Any) -> Dict[str, Any]:
        """Delete email by ID"""
        email_id = data if isinstance(data, str) else data.get('id')
        
        if not email_id:
            raise ComponentError("Email ID not specified for deletion")
            
        folder = self.uri.get_param('folder', 'INBOX')
        
        try:
            # Connect and login
            if self.use_ssl:
                mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                mail = imaplib.IMAP4(self.imap_host, self.imap_port)
                
            mail.login(self.user, self.password)
            mail.select(folder)
            
            # Mark for deletion
            mail.store(email_id.encode(), '+FLAGS', '\\Deleted')
            mail.expunge()
            
            mail.close()
            mail.logout()
            
            return {"success": True, "deleted": email_id}
            
        except Exception as e:
            raise ConnectionError(f"Failed to delete email: {e}")
            
    def _watch_inbox(self) -> List[Dict[str, Any]]:
        """Watch inbox for new emails (simple polling)"""
        # This is a simple implementation
        # For production, use IMAP IDLE or push notifications
        return self._read_emails()
        
    def _search_emails(self, data: Any) -> List[Dict[str, Any]]:
        """Search emails with criteria"""
        criteria = data if isinstance(data, str) else data.get('criteria', 'ALL')
        
        try:
            # Connect and search
            if self.use_ssl:
                mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                mail = imaplib.IMAP4(self.imap_host, self.imap_port)
                
            mail.login(self.user, self.password)
            mail.select('INBOX')
            
            # Search with criteria
            typ, data = mail.search(None, criteria)
            
            email_ids = data[0].split()
            emails = []
            
            for email_id in email_ids[:10]:  # Limit to 10 results
                typ, msg_data = mail.fetch(email_id, '(RFC822 FLAGS)')
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        emails.append({
                            "id": email_id.decode(),
                            "from": msg['From'],
                            "subject": msg['Subject'],
                            "date": msg['Date']
                        })
                        
            mail.close()
            mail.logout()
            
            return emails
            
        except Exception as e:
            raise ConnectionError(f"Failed to search emails: {e}")
            
    def _get_email_body(self, msg) -> str:
        """Extract email body from message"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
        return body
        
    def _get_attachments(self, msg) -> List[str]:
        """Get list of attachment filenames"""
        attachments = []
        
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    attachments.append(filename)
                    
        return attachments
        
    def _add_attachment(self, msg: MIMEMultipart, attachment: str):
        """Add attachment to email"""
        path = Path(attachment)
        
        if not path.exists():
            logger.warning(f"Attachment not found: {attachment}")
            return
            
        with open(path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {path.name}'
        )
        
        msg.attach(part)


@register("email-watch")
class EmailWatchComponent(StreamComponent):
    """Stream component for watching emails"""
    
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.email = EmailComponent(uri)
        self.interval = uri.get_param('interval', 60)  # Check every 60 seconds
        self.seen_ids = set()
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream new emails as they arrive"""
        logger.info(f"Watching for new emails every {self.interval} seconds")
        
        while True:
            try:
                emails = self.email._read_emails()
                
                for email_msg in emails:
                    email_id = email_msg['id']
                    if email_id not in self.seen_ids:
                        self.seen_ids.add(email_id)
                        yield email_msg
                        
            except Exception as e:
                logger.error(f"Error checking emails: {e}")
                
            time.sleep(self.interval)
            
    def process(self, data: Any) -> Any:
        """Get current emails"""
        return self.email._read_emails()


@register("email-filter")
class EmailFilterComponent(Component):
    """Filter emails based on criteria"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Filter emails"""
        if not isinstance(data, list):
            return data
            
        # Filter criteria
        from_filter = self.uri.get_param('from')
        subject_filter = self.uri.get_param('subject')
        has_attachments = self.uri.get_param('has_attachments')
        
        filtered = []
        
        for email_msg in data:
            if from_filter and from_filter not in email_msg.get('from', ''):
                continue
            if subject_filter and subject_filter not in email_msg.get('subject', ''):
                continue
            if has_attachments and not email_msg.get('attachments'):
                continue
                
            filtered.append(email_msg)
            
        return filtered
