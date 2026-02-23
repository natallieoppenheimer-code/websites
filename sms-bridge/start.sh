#!/bin/bash
cd /Users/paulocfborges/Desktop/dev/sms-bridge
export TEXTLINK_SMS_API_KEY=GmW3Hfv7tpxJTLhtOR2phT448ZHoh1JLYBIURx5PL2gmuSWyNdq4n5SoBI2axrai
export TEXTLINK_SMS_API_URL=https://textlinksms.com/api/send-sms
export BRAVE_API_KEY=BSAuJGG-s4NGXye31gqvGRrZEipYIBM
export BRAVE_API_URL=https://api.search.brave.com/res/v1/web/search
exec /usr/local/bin/python3.7 -m uvicorn app.main:app --host 0.0.0.0 --port 8001
