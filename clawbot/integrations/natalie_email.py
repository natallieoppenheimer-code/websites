"""
Natalie (Equestro Labs) email via DreamHost SMTP/IMAP.

Used when user_id is natalie@equestrolabs.com so OpenClaw and lead-gen
send/receive from the DreamHost-hosted mailbox (no Google OAuth).
"""
from __future__ import annotations

import os
import ssl
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional

# DreamHost defaults
DEFAULT_SMTP_HOST = "smtp.dreamhost.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_IMAP_HOST = "imap.dreamhost.com"
DEFAULT_IMAP_PORT = 993

# Natalie's signature (email + phone) — appended to all emails sent from this address
NATALIE_SIGNATURE = """\
Best,
Natalie
Equestro Labs | equestrolabs.com
natalie@equestrolabs.com | 669-258-7531"""


def _config() -> dict:
    return {
        "email": os.getenv("NATALIE_EMAIL", "natalie@equestrolabs.com"),
        "password": os.getenv("NATALIE_EMAIL_PASSWORD", ""),
        "smtp_host": os.getenv("NATALIE_SMTP_HOST", DEFAULT_SMTP_HOST),
        "smtp_port": int(os.getenv("NATALIE_SMTP_PORT", str(DEFAULT_SMTP_PORT))),
        "imap_host": os.getenv("NATALIE_IMAP_HOST", DEFAULT_IMAP_HOST),
        "imap_port": int(os.getenv("NATALIE_IMAP_PORT", str(DEFAULT_IMAP_PORT))),
    }


def is_natalie_email(user_id: str) -> bool:
    """True if user_id is the configured Natalie address (DreamHost mailbox)."""
    if not user_id:
        return False
    addr = _config()["email"].strip().lower()
    return user_id.strip().lower() == addr


class NatalieEmailService:
    """
    Send and receive email for natalie@equestrolabs.com via DreamHost SMTP/IMAP.
    API-compatible with GmailService for list_messages, get_message, send_message.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        cfg = _config()
        self.email = cfg["email"]
        self.password = cfg["password"]
        if not self.password:
            raise ValueError(
                "NATALIE_EMAIL_PASSWORD is not set. "
                "Set it in .env for natalie@equestrolabs.com (DreamHost)."
            )
        self.smtp_host = cfg["smtp_host"]
        self.smtp_port = cfg["smtp_port"]
        self.imap_host = cfg["imap_host"]
        self.imap_port = cfg["imap_port"]

    def list_messages(
        self,
        query: str = "",
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """List messages in INBOX. Supports Gmail-style query like 'is:unread' -> UNSEEN."""
        result = []
        ssl_ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=ssl_ctx) as imap:
            imap.login(self.email, self.password)
            imap.select("INBOX")
            # Map Gmail-style query to IMAP
            q = (query or "").strip().lower()
            if "unread" in q:
                search_criterion = "UNSEEN"
            else:
                search_criterion = "ALL"
            status, msg_ids = imap.uid("SEARCH", None, search_criterion)
            if status != "OK" or not msg_ids[0]:
                imap.logout()
                return result
            ids = msg_ids[0].split()
            # Newest first (higher UID = newer), limit
            ids = ids[-max_results:] if len(ids) > max_results else ids
            ids.reverse()
            for mid in ids:
                result.append({"id": mid.decode("ascii"), "threadId": ""})
            imap.logout()
        return result

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """Fetch one message by ID (IMAP sequence or UID)."""
        ssl_ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=ssl_ctx) as imap:
            imap.login(self.email, self.password)
            imap.select("INBOX")
            try:
                # message_id from list_messages is UID (string of digits)
                status, data = imap.uid("FETCH", message_id, "(RFC822)")
            except Exception:
                status, data = "NO", [None]
            if status != "OK" or not data or data[0] is None:
                imap.logout()
                raise Exception(f"Message not found: {message_id}")
            raw = data[0][1]
            if isinstance(raw, bytes):
                msg = email.message_from_bytes(raw)
            else:
                msg = email.message_from_string(raw)
            imap.logout()
        return self._parse_message(msg, message_id)

    @staticmethod
    def _parse_message(msg: email.message.Message, message_id: str) -> Dict[str, Any]:
        subject = msg.get("Subject", "")
        from_ = msg.get("From", "")
        to = msg.get("To", "")
        date = msg.get("Date", "")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except Exception:
                        body = part.get_payload(decode=True).decode("latin-1", errors="replace")
                    break
                elif part.get_content_type() == "text/html" and not body:
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except Exception:
                        body = part.get_payload(decode=True).decode("latin-1", errors="replace")
        else:
            try:
                body = msg.get_payload(decode=True)
                body = (body or b"").decode("utf-8", errors="replace")
            except Exception:
                body = ""
        snippet = (body or "")[:200].replace("\n", " ")
        return {
            "id": message_id,
            "thread_id": "",
            "subject": subject,
            "from": from_,
            "to": to,
            "date": date,
            "snippet": snippet,
            "body": body,
            "labels": [],
        }

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        body_type: str = "plain",
    ) -> Dict[str, Any]:
        """Send an email via DreamHost SMTP (STARTTLS on 587). Appends Natalie's signature if not present."""
        if "669-258-7531" not in body and NATALIE_SIGNATURE.strip() not in body:
            body = body.rstrip() + "\n\n" + NATALIE_SIGNATURE
        message = MIMEText(body, body_type)
        message["From"] = self.email
        message["To"] = to
        message["Subject"] = subject
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(self.email, self.password)
            smtp.sendmail(self.email, [to], message.as_string())
        return {"id": "", "thread_id": "", "label_ids": []}

    def get_labels(self) -> List[Dict[str, Any]]:
        """IMAP doesn't have Gmail-style labels; return INBOX-only for compatibility."""
        return [{"id": "INBOX", "name": "INBOX", "type": "system"}]
