# Clawbot - Google Workspace Integration Bot

A comprehensive FastAPI-based bot that integrates with Google Workspace services including Gmail, Google Calendar, and GSuite Admin API. Features token caching, multi-agent routing, and optimized API access.

## OpenClaw vs Clawbot (important)

- **OpenClaw** = the assistant you already use (TUI + gateway at `ws://127.0.0.1:18789`). It is a **separate app**; we don’t have its code in this repo.
- **Clawbot** = **this project** – an HTTP API that adds Gmail, Calendar, Memory, and SMS. It runs at `http://localhost:8000`.

To have “OpenClaw set up correctly” with Gmail/Calendar/Memory/SMS, you need: **(1)** Clawbot running (`./start_clawbot.sh`), **(2)** OpenClaw running (`openclaw tui ...`), and **(3)** OpenClaw configured to call Clawbot at `http://localhost:8000`. See **[README_OPENCLAW_VS_CLAWBOT.md](README_OPENCLAW_VS_CLAWBOT.md)** and **[CONNECT_OPENCLAW.md](CONNECT_OPENCLAW.md)**.

## Features

- 🔐 **Google OAuth2 Authentication** with automatic token refresh
- 📧 **Gmail Integration** - Read, send, and manage emails
- 📅 **Google Calendar Integration** - Create, update, and manage events
- 👥 **GSuite Admin API** - Manage users and groups
- 💾 **Token Caching** - File-based or Redis-backed token caching
- 🤖 **Multi-Agent Routing** - Intelligent request routing with multiple strategies
- 🧠 **Memory System** - Daily context windows and long-term memory for OpenClaw
- ⚡ **Optimized Performance** - Token refresh, load balancing, and efficient API usage

## Local Development (Mac Mini)

**Running OpenClaw locally?** Use Clawbot locally too!

- **[LOCAL_SETUP.md](LOCAL_SETUP.md)** - Complete local setup guide
- **[OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md)** - OpenClaw integration guide

**Quick Start:**
```bash
./start_clawbot.sh
```

Then access:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## Deployment (Optional)

If you want to deploy to cloud:

- **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** - Fast 5-minute deployment guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment documentation
- **[DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)** - Step-by-step checklist

## Quick Start

### 1. Prerequisites

- Python 3.8+
- Google Cloud Project with APIs enabled
- (Optional) Redis for token caching

### 2. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Gmail API
   - Google Calendar API
   - Admin SDK API (for GSuite)
4. Create OAuth 2.0 credentials:
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Choose **Web application**
   - Add authorized redirect URI: `http://localhost:8000/auth/callback` (or your production URL)
   - Save the Client ID and Client Secret

### 3. Installation

```bash
# Clone or navigate to the project directory
cd /Users/paulocfborges/Desktop/dev

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Google OAuth credentials:

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

### 5. Run the Application

```bash
# Run with uvicorn
uvicorn clawbot_api:app --host 0.0.0.0 --port 8000 --reload

# Or use the main.py for SMS functionality
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Usage

### Authentication Flow

1. **Get Authorization URL:**
   ```bash
   curl "http://localhost:8000/auth/authorize?user_id=user123"
   ```

2. **User visits the authorization URL** and grants permissions

3. **Handle OAuth Callback:**
   ```bash
   curl "http://localhost:8000/auth/callback?code=AUTHORIZATION_CODE&user_id=user123"
   ```

4. **Check Authentication Status:**
   ```bash
   curl "http://localhost:8000/auth/status/user123"
   ```

### Gmail Operations

**List Messages:**
```bash
curl "http://localhost:8000/gmail/messages?user_id=user123&query=is:unread&max_results=10"
```

**Send Email:**
```bash
curl -X POST "http://localhost:8000/gmail/send?user_id=user123&to=recipient@example.com&subject=Hello&body=Test%20message"
```

### Calendar Operations

**List Events:**
```bash
curl "http://localhost:8000/calendar/events?user_id=user123&max_results=10"
```

**Create Event:**
```bash
curl -X POST "http://localhost:8000/calendar/events?user_id=user123&summary=Meeting&start_time=2024-01-01T10:00:00Z&end_time=2024-01-01T11:00:00Z"
```

### GSuite Operations

**List Users:**
```bash
curl "http://localhost:8000/gsuite/users?user_id=user123&domain=example.com"
```

**List Groups:**
```bash
curl "http://localhost:8000/gsuite/groups?user_id=user123"
```

### Multi-Agent Routing

**Route a Request:**
```bash
curl -X POST "http://localhost:8000/route" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "intent": "gmail",
    "action": "send_email",
    "text": "Send an email to john@example.com"
  }'
```

**Register an Agent:**
```bash
curl -X POST "http://localhost:8000/agents/register" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "custom_agent_1",
    "name": "Custom Agent",
    "type": "custom",
    "capabilities": ["custom", "specialized"],
    "available": true,
    "max_load": 20
  }'
```

## Token Caching

### File-Based Caching (Default)

Tokens are stored in `.token_cache/` directory. This is suitable for single-instance deployments.

### Redis Caching

For multi-instance deployments, use Redis:

1. Install Redis:
   ```bash
   # macOS
   brew install redis
   
   # Ubuntu/Debian
   sudo apt-get install redis-server
   ```

2. Update `.env`:
   ```env
   TOKEN_CACHE_TYPE=redis
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

3. Start Redis:
   ```bash
   redis-server
   ```

## Multi-Agent Routing Strategies

### Round Robin
Routes requests sequentially through available agents.

### Load Balance
Routes to the agent with the lowest current load.

### Intent-Based (Default)
Routes based on request intent and agent capabilities:
- Gmail requests → Gmail agents
- Calendar requests → Calendar agents
- GSuite requests → GSuite agents

### Random
Randomly selects from available agents.

Configure strategy in `.env`:
```env
AGENT_ROUTING_STRATEGY=intent_based
```

## Memory System

Clawbot includes a comprehensive memory system for OpenClaw integration:

- **Daily Context**: Track and retrieve today's conversations
- **Long-term Memory**: Store important information over extended periods
- **Conversation History**: Maintain context across sessions
- **User Profiles**: Build comprehensive user understanding

See [MEMORY_SYSTEM.md](MEMORY_SYSTEM.md) for detailed documentation.

**Quick Example:**
```bash
# Store a memory
curl -X POST "http://localhost:8000/memory/store?user_id=user123&content=User%20prefers%20morning%20meetings&importance=0.8"

# Get today's context
curl "http://localhost:8000/memory/daily?user_id=user123"

# Get long-term summary
curl "http://localhost:8000/memory/long-term/summary?user_id=user123&days=30"
```

## API Documentation

Full interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
.
├── clawbot/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── oauth.py           # Google OAuth2 handling
│   │   └── token_cache.py     # Token caching system
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── gmail.py           # Gmail API integration
│   │   ├── calendar.py        # Calendar API integration
│   │   └── gsuite.py          # GSuite Admin API integration
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── memory_store.py    # Core memory storage
│   │   ├── daily_context.py   # Daily context management
│   │   └── long_term_memory.py # Long-term memory
│   └── routing/
│       ├── __init__.py
│       ├── router.py          # Multi-agent router
│       └── strategies.py      # Routing strategies
├── clawbot_api.py             # Main FastAPI application
├── main.py                     # SMS API (legacy)
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## Security Considerations

1. **Token Storage**: Tokens are stored securely with file permissions (600) or in Redis
2. **HTTPS**: Always use HTTPS in production
3. **Environment Variables**: Never commit `.env` file to version control
4. **OAuth Scopes**: Only request necessary scopes
5. **Token Refresh**: Tokens are automatically refreshed before expiration

## Troubleshooting

### "No valid credentials found"
- Ensure user has completed OAuth flow
- Check token cache directory permissions
- Verify credentials haven't expired

### "Insufficient permissions"
- Check OAuth scopes in Google Cloud Console
- Ensure user granted all required permissions
- For GSuite Admin API, domain-wide delegation may be required

### Redis Connection Errors
- Verify Redis is running: `redis-cli ping`
- Check Redis host/port in `.env`
- Ensure Redis password is correct if set

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Style

```bash
# Install formatters
pip install black isort

# Format code
black clawbot/
isort clawbot/
```

## License

MIT License

## Support

For issues and questions, please open an issue on the repository.
