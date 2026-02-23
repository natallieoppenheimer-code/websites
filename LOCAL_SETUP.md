# Local Development Setup for Mac Mini

Run Clawbot locally on your Mac Mini alongside OpenClaw.

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/paulocfborges/Desktop/dev

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your Google OAuth credentials
# Make sure GOOGLE_REDIRECT_URI is set to:
# GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

### 3. Start Clawbot API

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the API
uvicorn clawbot_api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

### 4. Configure OpenClaw

In your OpenClaw configuration, add Clawbot as a custom API:

**API Endpoint:** `http://localhost:8000`

**Available endpoints for OpenClaw:**
- `/gmail/messages` - List Gmail messages
- `/gmail/send` - Send emails
- `/calendar/events` - List calendar events
- `/calendar/events` (POST) - Create events
- `/memory/store` - Store memories
- `/memory/daily` - Get daily context
- `/memory/long-term/summary` - Get long-term memory

## Running Both Services

### Option 1: Separate Terminals

**Terminal 1 - Clawbot:**
```bash
cd /Users/paulocfborges/Desktop/dev
source .venv/bin/activate
uvicorn clawbot_api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - OpenClaw:**
```bash
# Your OpenClaw startup command
```

### Option 2: Background Process

```bash
# Start Clawbot in background
cd /Users/paulocfborges/Desktop/dev
source .venv/bin/activate
nohup uvicorn clawbot_api:app --host 0.0.0.0 --port 8000 --reload > clawbot.log 2>&1 &

# Check if running
curl http://localhost:8000/health

# View logs
tail -f clawbot.log

# Stop when needed
pkill -f "uvicorn clawbot_api"
```

### Option 3: Using Docker Compose (Optional)

If you prefer containerized setup:

```bash
# Start both Redis and Clawbot
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Google OAuth Setup for Local Development

### 1. Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. **APIs & Services** → **Credentials**
3. Create OAuth 2.0 Client ID:
   - **Application type:** Web application
   - **Name:** Clawbot Local Dev
   - **Authorized redirect URIs:**
     - `http://localhost:8000/auth/callback`
     - `http://127.0.0.1:8000/auth/callback`
4. Copy Client ID and Client Secret

### 2. Configure `.env`

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
TOKEN_CACHE_TYPE=file
TOKEN_CACHE_PATH=./.token_cache
```

## Memory Storage (Local)

By default, Clawbot uses file-based storage:

- **Token cache:** `.token_cache/` directory
- **Memory store:** `.memory_store/` directory

These are created automatically and stored locally on your Mac Mini.

### Optional: Use Redis Locally

If you want Redis for better performance:

```bash
# Install Redis (macOS)
brew install redis

# Start Redis
brew services start redis

# Update .env
TOKEN_CACHE_TYPE=redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Testing the Setup

### 1. Verify API is Running

```bash
curl http://localhost:8000/health
# Should return: {"ok": true, ...}
```

### 2. Test OAuth Flow

```bash
# Get authorization URL
curl "http://localhost:8000/auth/authorize?user_id=test_user"

# Open the URL in browser, grant permissions
# You'll be redirected to callback with code

# Exchange code for token (replace CODE with actual code)
curl "http://localhost:8000/auth/callback?code=CODE&user_id=test_user"
```

### 3. Test Memory System

```bash
# Store a memory
curl -X POST "http://localhost:8000/memory/store?user_id=test_user&content=Test%20memory&importance=0.8"

# Get daily context
curl "http://localhost:8000/memory/daily?user_id=test_user"
```

### 4. Test Gmail Integration

```bash
# List messages (after OAuth)
curl "http://localhost:8000/gmail/messages?user_id=test_user&max_results=5"
```

## Integration with OpenClaw

### Method 1: Custom API/Tool

In OpenClaw, add Clawbot endpoints as custom APIs:

**Example - Gmail Integration:**
- **Name:** Gmail List Messages
- **URL:** `http://localhost:8000/gmail/messages`
- **Method:** GET
- **Headers:** None
- **Query Params:** `user_id`, `query`, `max_results`

**Example - Memory Storage:**
- **Name:** Store Memory
- **URL:** `http://localhost:8000/memory/store`
- **Method:** POST
- **Query Params:** `user_id`, `content`, `role`, `importance`

### Method 2: Direct API Calls

OpenClaw can make HTTP requests directly to Clawbot:

```python
# Example in OpenClaw
import requests

# Store memory
response = requests.post(
    "http://localhost:8000/memory/store",
    params={
        "user_id": user_id,
        "content": message_content,
        "role": "user",
        "importance": 0.5
    }
)

# Get daily context
response = requests.get(
    "http://localhost:8000/memory/daily",
    params={"user_id": user_id}
)
```

## Startup Script

Create a convenient startup script:

```bash
#!/bin/bash
# start_clawbot.sh

cd /Users/paulocfborges/Desktop/dev
source .venv/bin/activate
uvicorn clawbot_api:app --host 0.0.0.0 --port 8000 --reload
```

Make it executable:
```bash
chmod +x start_clawbot.sh
```

Run:
```bash
./start_clawbot.sh
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn clawbot_api:app --host 0.0.0.0 --port 8001
```

### OAuth Redirect Issues

- Make sure redirect URI in Google Console matches exactly: `http://localhost:8000/auth/callback`
- Check `.env` file has correct `GOOGLE_REDIRECT_URI`
- Try `http://127.0.0.1:8000/auth/callback` if localhost doesn't work

### Memory Not Persisting

- Check `.memory_store/` directory exists and is writable
- Verify file permissions: `chmod 755 .memory_store`
- Check disk space: `df -h`

### Import Errors

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Development Tips

1. **Auto-reload:** The `--reload` flag automatically restarts on code changes
2. **Logs:** Check terminal output for errors
3. **API Docs:** Visit http://localhost:8000/docs for interactive API testing
4. **Health Check:** Use `/health` endpoint to verify service is running
5. **Memory Management:** Clear old memories periodically:
   ```bash
   curl -X DELETE "http://localhost:8000/memory/clear?user_id=test_user&older_than_days=30"
   ```

## Next Steps

1. ✅ Start Clawbot API locally
2. ✅ Complete OAuth flow for your user
3. ✅ Configure OpenClaw to use Clawbot endpoints
4. ✅ Test integrations (Gmail, Calendar, Memory)
5. ✅ Start using in your workflows!

## Keeping Services Running

### Using launchd (macOS)

Create `~/Library/LaunchAgents/com.clawbot.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.clawbot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/paulocfborges/Desktop/dev/.venv/bin/uvicorn</string>
        <string>clawbot_api:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/paulocfborges/Desktop/dev</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.clawbot.plist
```

Unload:
```bash
launchctl unload ~/Library/LaunchAgents/com.clawbot.plist
```
