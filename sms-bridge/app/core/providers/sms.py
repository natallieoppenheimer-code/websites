from abc import ABC, abstractmethod
import httpx
from typing import Dict
from app.config import settings


class SMSClient(ABC):
    @abstractmethod
    async def send(self, to: str, message: str) -> dict:
        ...


class TextLinkSMSProvider(SMSClient):
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url

    async def send(self, to: str, message: str) -> dict:
        # Correct field names per TextLink API docs: phone_number + text
        payload = {"phone_number": to, "text": message}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.api_url, json=payload, headers=headers)
        ok = resp.status_code in (200, 201, 202)
        try:
            body = resp.json()
            # TextLink returns {"ok": true} on success
            ok = ok and body.get("ok", False)
        except Exception:
            body = {"raw": resp.text}
        return {"ok": ok, "status": resp.status_code, "response_body": body}


# Provider registry
providers: Dict[str, SMSClient] = {
    "textlink_sms": TextLinkSMSProvider(
        api_key=settings.textlink_sms_api_key,
        api_url=settings.textlink_sms_api_url,
    ),
}


def get_provider(name: str) -> SMSClient:
    if name not in providers:
        raise ValueError(f"Unknown provider: {name}")
    return providers[name]
