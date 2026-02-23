#!/bin/bash
# Start the full stack: Clawbot API + instructions for OpenClaw
# Wraps everything with caffeinate so the Mac never sleeps while running.
# This gives you ONE place to start everything.

set -e

# Prevent Mac from sleeping while this stack is running.
# caffeinate -i keeps the system awake; -w <pid> exits when this script exits.
# We re-exec ourselves under caffeinate on the first run (CAFFEINATED is unset).
if [ -z "$CAFFEINATED" ]; then
    echo "Keeping Mac awake with caffeinate..."
    CAFFEINATED=1 exec caffeinate -i "$0" "$@"
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  OpenClaw + Clawbot – Full stack startup"
echo "=============================================="
echo ""

# 1. Start Clawbot in background
echo "1. Starting Clawbot API (http://localhost:8000)..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Kill any existing Clawbot on 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "   Port 8000 in use – stopping existing process..."
    kill -9 $(lsof -ti :8000) 2>/dev/null || true
    sleep 2
fi

nohup uvicorn clawbot_api:app --host 0.0.0.0 --port 8000 > clawbot.log 2>&1 &
CLAWBOT_PID=$!
echo "   Clawbot started (PID $CLAWBOT_PID). Logs: clawbot.log"
sleep 3

# 2. Health check
if curl -sS http://localhost:8000/health >/dev/null 2>&1; then
    echo "   Clawbot is up: http://localhost:8000"
else
    echo "   WARNING: Clawbot health check failed. Check clawbot.log"
fi
echo ""

# 3. Tell user to start OpenClaw
echo "2. Start OpenClaw in another terminal:"
echo ""
echo "   openclaw tui \\"
echo "     --url ws://127.0.0.1:18789 \\"
echo "     --password CrazyClaw1!"
echo ""
echo "   (Start the OpenClaw gateway first if it’s not already running.)"
echo ""
echo "3. Configure OpenClaw to use Clawbot:"
echo "   - In OpenClaw’s config, set custom API / tools base URL to:"
echo "     http://localhost:8000"
echo "   - See CONNECT_OPENCLAW.md and README_OPENCLAW_VS_CLAWBOT.md for details."
echo ""
echo "=============================================="
echo "  Clawbot API:  http://localhost:8000"
echo "  API docs:     http://localhost:8000/docs"
echo "  To stop:      pkill -f 'uvicorn clawbot_api'"
echo "=============================================="
