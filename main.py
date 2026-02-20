import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="TextLink SMS API", version="1.0.0")

TEXTLINK_API_URL = "https://textlinksms.com/api/send-sms"
API_KEY = os.getenv("TEXTLINK_API_KEY")


class SendSMSRequest(BaseModel):
    phone_number: str = Field(..., description="Recipient phone number with country prefix, e.g. +11234567890")
    text: str = Field(..., description="Message body")
    sim_card_id: Optional[int] = Field(None, description="Optional SIM card ID to send from")
    custom_id: Optional[str] = Field(None, description="Optional custom ID for failed message webhook")


class SendSMSResponse(BaseModel):
    ok: bool
    message: Optional[str] = None
    queued: Optional[bool] = None


@app.post("/send-sms", response_model=SendSMSResponse)
async def send_sms(body: SendSMSRequest) -> SendSMSResponse:
    """Send an SMS via TextLink API."""
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="TEXTLINK_API_KEY environment variable is not set",
        )

    payload = {
        "phone_number": body.phone_number,
        "text": body.text,
    }
    if body.sim_card_id is not None:
        payload["sim_card_id"] = body.sim_card_id
    if body.custom_id is not None:
        payload["custom_id"] = body.custom_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TEXTLINK_API_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
            timeout=30.0,
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text or "TextLink API error",
        )

    data = response.json()
    return SendSMSResponse(
        ok=data.get("ok", False),
        message=data.get("message"),
        queued=data.get("queued"),
    )


@app.get("/")
async def root():
    return {"message": "TextLink SMS API proxy", "docs": "/docs"}


@app.get("/health")
async def health():
    """For Render / OpenClaw platform health checks."""
    return {"ok": True}
