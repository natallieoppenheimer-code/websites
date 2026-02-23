"""Gmail API integration"""
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from clawbot.auth.oauth import get_google_credentials
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class GmailService:
    """Gmail API service wrapper"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.credentials = get_google_credentials(user_id)
        if not self.credentials:
            raise ValueError(f"No valid credentials found for user {user_id}")
        self.service = build('gmail', 'v1', credentials=self.credentials)
    
    def list_messages(
        self, 
        query: str = "", 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """List messages matching query"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            return messages
        except Exception as e:
            raise Exception(f"Error listing messages: {str(e)}")
    
    def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get full message details"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return self._parse_message(message)
        except Exception as e:
            raise Exception(f"Error getting message: {str(e)}")
    
    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into readable format"""
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        # Extract headers
        header_dict = {h['name']: h['value'] for h in headers}
        
        # Extract body
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            data = payload.get('body', {}).get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return {
            'id': message['id'],
            'thread_id': message.get('threadId'),
            'subject': header_dict.get('Subject', ''),
            'from': header_dict.get('From', ''),
            'to': header_dict.get('To', ''),
            'date': header_dict.get('Date', ''),
            'snippet': message.get('snippet', ''),
            'body': body,
            'labels': message.get('labelIds', [])
        }
    
    def send_message(
        self, 
        to: str, 
        subject: str, 
        body: str, 
        body_type: str = 'plain'
    ) -> Dict[str, Any]:
        """Send an email message"""
        try:
            message = MIMEText(body, body_type)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'id': send_message['id'],
                'thread_id': send_message.get('threadId'),
                'label_ids': send_message.get('labelIds', [])
            }
        except Exception as e:
            raise Exception(f"Error sending message: {str(e)}")
    
    def send_message_with_attachments(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: List[Dict[str, Any]] = None,
        body_type: str = 'plain'
    ) -> Dict[str, Any]:
        """Send an email with attachments"""
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            msg_body = MIMEText(body, body_type)
            message.attach(msg_body)
            
            # Add attachments if provided
            if attachments:
                for att in attachments:
                    attachment = MIMEText(att.get('content', ''))
                    attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=att.get('filename', 'attachment')
                    )
                    message.attach(attachment)
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'id': send_message['id'],
                'thread_id': send_message.get('threadId'),
                'label_ids': send_message.get('labelIds', [])
            }
        except Exception as e:
            raise Exception(f"Error sending message with attachments: {str(e)}")
    
    def create_draft(
        self, 
        to: str, 
        subject: str, 
        body: str
    ) -> Dict[str, Any]:
        """Create a draft message"""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={
                    'message': {'raw': raw_message}
                }
            ).execute()
            
            return draft
        except Exception as e:
            raise Exception(f"Error creating draft: {str(e)}")
    
    def get_labels(self) -> List[Dict[str, Any]]:
        """Get all Gmail labels"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            return results.get('labels', [])
        except Exception as e:
            raise Exception(f"Error getting labels: {str(e)}")
