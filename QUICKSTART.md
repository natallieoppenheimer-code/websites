# Clawbot Quick Start Guide

Get Clawbot up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Enable APIs:
   - Gmail API
   - Google Calendar API
   - Admin SDK API
4. Create OAuth 2.0 credentials:
   - **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URI: `http://localhost:8000/auth/callback`

## Step 3: Set Up Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your credentials:
# GOOGLE_CLIENT_ID=your_client_id
# GOOGLE_CLIENT_SECRET=your_client_secret
# GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

## Step 4: Verify Setup

```bash
python setup_clawbot.py
```

This will check:
- ✓ Dependencies installed
- ✓ Directory structure
- ✓ Environment variables
- ✓ Token cache setup

## Step 5: Start the API

```bash
uvicorn clawbot_api:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

## Step 6: Authenticate a User

1. **Get authorization URL:**
   ```bash
   curl "http://localhost:8000/auth/authorize?user_id=test_user"
   ```

2. **Open the URL in browser** and grant permissions

3. **Handle callback** (you'll be redirected automatically, or use the code from the URL):
   ```bash
   curl "http://localhost:8000/auth/callback?code=AUTHORIZATION_CODE&user_id=test_user"
   ```

4. **Verify authentication:**
   ```bash
   curl "http://localhost:8000/auth/status/test_user"
   ```

## Step 7: Use the API!

### Send an Email
```bash
curl -X POST "http://localhost:8000/gmail/send?user_id=test_user&to=recipient@example.com&subject=Hello&body=Test%20message"
```

### List Calendar Events
```bash
curl "http://localhost:8000/calendar/events?user_id=test_user"
```

### Create Calendar Event
```bash
curl -X POST "http://localhost:8000/calendar/events?user_id=test_user&summary=Meeting&start_time=2024-01-01T10:00:00Z&end_time=2024-01-01T11:00:00Z"
```

### List GSuite Users
```bash
curl "http://localhost:8000/gsuite/users?user_id=test_user&domain=example.com"
```

## Multi-Agent Routing

Route requests intelligently:

```bash
curl -X POST "http://localhost:8000/route" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "intent": "gmail",
    "action": "send_email"
  }'
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API at http://localhost:8000/docs
- Check out routing strategies in `.env`: `AGENT_ROUTING_STRATEGY`

## Troubleshooting

**"No valid credentials found"**
- Complete OAuth flow first (Step 6)

**"Insufficient permissions"**
- Check that all required APIs are enabled in Google Cloud Console
- Ensure user granted all permissions during OAuth flow

**Import errors**
- Run `pip install -r requirements.txt` again
- Check Python version: `python --version` (needs 3.8+)
