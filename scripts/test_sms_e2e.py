#!/usr/bin/env python3
"""
End-to-end test for SMS sending (TextLink) and optional voice note.
Run from project root: python scripts/test_sms_e2e.py
"""
import os
import sys

# Load .env from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import httpx

TRIAL_PHONE = "+14086075948"
TEXTLINK_URL = "https://textlinksms.com/api/send-sms"
CLAWBOT_URL = "http://localhost:8000"


def main():
    api_key = os.getenv("TEXTLINK_API_KEY")
    if not api_key:
        print("FAIL: TEXTLINK_API_KEY not set in .env")
        return 1

    print("=== 1. TextLink API direct (simple SMS) ===")
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                TEXTLINK_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "phone_number": TRIAL_PHONE,
                    "text": "E2E test: TextLink direct. If you get this, TextLink works.",
                },
            )
        print(f"  Status: {r.status_code}")
        print(f"  Body:   {r.text}")
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code != 200:
            print("  -> TextLink returned non-200")
        elif not data.get("ok"):
            print("  -> TextLink returned ok: false — check message above (e.g. no SIM/device)")
        elif data.get("queued"):
            print("  -> TextLink QUEUED (all senders busy). Message should send when a device is free; check phone shortly.")
        else:
            print("  -> TextLink accepted message (check phone for delivery)")
    except Exception as e:
        print(f"  ERROR: {e}")
        return 1

    print("\n=== 2. Clawbot /send-sms (no voice note) ===")
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(
                f"{CLAWBOT_URL}/send-sms",
                json={
                    "phone_number": TRIAL_PHONE,
                    "text": "E2E test: Clawbot SMS only (no voice). If you get this, /send-sms works.",
                    "include_voice_note": False,
                },
            )
        print(f"  Status: {r.status_code}")
        print(f"  Body:   {r.text}")
        if r.status_code != 200:
            print("  -> Clawbot returned error")
            return 1
        try:
            j = r.json()
            if j.get("textlink", {}).get("queued"):
                print("  -> Clawbot OK; TextLink QUEUED — delivery when device free.")
            else:
                print("  -> Clawbot accepted (check phone)")
        except Exception:
            print("  -> Clawbot accepted (check phone)")
    except httpx.ConnectError as e:
        print(f"  ERROR: Cannot reach Clawbot at {CLAWBOT_URL}. Start API: uvicorn clawbot_api:app --port 8000")
        return 1
    except Exception as e:
        print(f"  ERROR: {e}")
        return 1

    print("\n=== 3. Clawbot /send-sms WITH voice note ===")
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                f"{CLAWBOT_URL}/send-sms",
                json={
                    "phone_number": TRIAL_PHONE,
                    "text": "E2E test: Clawbot with voice note. You should see a link below.",
                    "include_voice_note": True,
                },
            )
        print(f"  Status: {r.status_code}")
        print(f"  Body:   {r.text}")
        if r.status_code != 200:
            print("  -> Clawbot returned error")
            return 1
        try:
            j = r.json()
            if j.get("textlink", {}).get("queued"):
                print("  -> Clawbot OK; TextLink QUEUED — SMS + voice link when device free.")
            else:
                print("  -> Clawbot accepted (check phone for SMS + voice note link)")
        except Exception:
            print("  -> Clawbot accepted (check phone for SMS + voice note link)")
    except Exception as e:
        print(f"  ERROR: {e}")
        return 1

    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
