# Scripts

## Lead pipeline E2E test (one lead)

Runs the full lead pipeline (source → BizFile → People Search → Touch 1) for one lead so you can verify every aspect.

```bash
# From project root. Ensure .env has: LEAD_GEN_SHEET_ID, RAPIDAPI_LEAD_KEY, RAPIDAPI_PEOPLE_KEY, CLAWBOT_BASE_URL.
# For Sheets write: authorize once at http://localhost:8000/auth/authorize?user_id=YOUR_GOOGLE_EMAIL

# Dry run: inject one test lead, run pipeline, no real SMS/email
python scripts/test_lead_pipeline_e2e.py --inject --dry-run

# Live: inject one lead with your phone, send real Touch 1 (Clawbot API must be running; TEXTLINK_API_KEY set)
python scripts/test_lead_pipeline_e2e.py --inject --phone "+1XXXXXXXXXX"

# Process at most 1 lead from RapidAPI/pending (no inject)
python scripts/test_lead_pipeline_e2e.py --max-leads 1 --dry-run
```

Optional: `BIZFILE_EMAIL`, `BIZFILE_PASSWORD` for BizFile owner lookup; `TEST_LEAD_PHONE` instead of `--phone`.

**E2E via API (no local Python 3.9+ needed):** Start the API (e.g. on Render or `uvicorn clawbot_api:app --port 8000`), then:

```bash
BASE_URL=http://localhost:8000 ./scripts/run_e2e_via_api.sh
```

Or manually: `POST /leads/inject` with JSON body (area, category, business_name, biz_phone), then `POST /leads/run/sync?area=...&category=...&max_to_process=1&dry_run=true`.

---

## SMS E2E test

```bash
# From project root; ensure Clawbot API is running (e.g. uvicorn clawbot_api:app --port 8000)
python scripts/test_sms_e2e.py
```

Runs three checks:

1. **TextLink API direct** – Sends a plain SMS via TextLink. Confirms API key and number format.
2. **Clawbot /send-sms (no voice)** – Sends via Clawbot; no voice note.
3. **Clawbot /send-sms with voice note** – Sends SMS + voice note link (if `ELEVENLABS_API_KEY` is set).

### Not receiving SMS?

- **`queued: true`** – TextLink accepted the message but all senders (SIMs) are busy. Messages are sent when a device is free. Check [TextLink dashboard](https://textlinksms.com/dashboard) → Devices to see SIM status and queue.
- **Wrong number** – Use E.164: `+14086075948` (US).
- **Carrier / spam** – Some carriers delay or filter; check spam/blocked.
