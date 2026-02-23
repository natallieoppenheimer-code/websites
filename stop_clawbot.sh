#!/bin/bash
# Stop Clawbot API

echo "🛑 Stopping Clawbot API..."

# Find and kill uvicorn process running clawbot_api
pkill -f "uvicorn clawbot_api:app" || echo "No Clawbot process found"

echo "✅ Clawbot stopped"
