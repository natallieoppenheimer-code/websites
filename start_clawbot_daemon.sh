#!/bin/bash
# Non-interactive daemon script for launchd
cd /Users/paulocfborges/Desktop/dev

# Unset webhook secret so any inbound SMS is accepted (allowlist removed per Paul's request)
unset TEXTLINK_WEBHOOK_SECRET

# Use the venv Python
exec /Users/paulocfborges/Desktop/dev/.venv/bin/uvicorn clawbot_api:app \
    --host 0.0.0.0 \
    --port 8000
