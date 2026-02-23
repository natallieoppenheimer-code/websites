#!/bin/bash
# Start Clawbot API locally for Mac Mini

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Clawbot API..."
echo "=========================="
echo ""

# Prefer Python 3.13 (Homebrew), fall back to whatever python3 is available
PYTHON_BIN="/opt/homebrew/bin/python3.13"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(which python3)"
fi

# Rebuild the venv if it doesn't exist or is running on Python < 3.10
NEEDS_REBUILD=false
if [ ! -d ".venv" ]; then
    NEEDS_REBUILD=true
else
    VENV_PYVER="$(.venv/bin/python --version 2>&1 | awk '{print $2}')"
    VENV_MINOR="$(echo "$VENV_PYVER" | cut -d. -f2)"
    if [ "${VENV_MINOR:-0}" -lt 10 ]; then
        echo "⚠️  venv is on Python $VENV_PYVER (< 3.10) — rebuilding with $($PYTHON_BIN --version)..."
        rm -rf .venv
        NEEDS_REBUILD=true
    fi
fi

if [ "$NEEDS_REBUILD" = true ]; then
    echo "📦 Creating virtual environment with $($PYTHON_BIN --version)..."
    "$PYTHON_BIN" -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your Google OAuth credentials"
    echo ""
fi

# Create directories
mkdir -p .token_cache .memory_store

# Check if port is available
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is already in use"
    echo "Trying to find the process..."
    lsof -i :8000
    echo ""
    read -p "Kill the process and continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill -9 $(lsof -ti :8000)
        echo "✅ Port 8000 freed"
    else
        echo "❌ Exiting. Please free port 8000 or use a different port"
        exit 1
    fi
fi

echo "✅ Starting Clawbot API on http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "❤️  Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the API — unset webhook secret so any inbound SMS is accepted
unset TEXTLINK_WEBHOOK_SECRET
exec .venv/bin/uvicorn clawbot_api:app --host 0.0.0.0 --port 8000 --reload
