# OpenClaw Integration Guide

How to integrate Clawbot with OpenClaw running locally on your Mac Mini.

## Overview

Clawbot runs as a local API service that OpenClaw can call to:
- Access Gmail, Calendar, and GSuite
- Store and retrieve conversation memories
- Maintain daily context and long-term memory

## Setup

### 1. Start Clawbot

```bash
cd /Users/paulocfborges/Desktop/dev
./start_clawbot.sh
```

Or manually:
```bash
source .venv/bin/activate
uvicorn clawbot_api:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Verify Clawbot is Running

```bash
curl http://localhost:8000/health
```

Should return: `{"ok": true, ...}`

## Integration Methods

### Method 1: Custom API Endpoints in OpenClaw

Add Clawbot endpoints as custom APIs in OpenClaw configuration.

#### Gmail Integration

**List Messages:**
- **Name:** `clawbot_gmail_list`
- **URL:** `http://localhost:8000/gmail/messages`
- **Method:** GET
- **Query Parameters:**
  - `user_id` (required): Your user ID
  - `query` (optional): Gmail search query (e.g., "is:unread")
  - `max_results` (optional): Number of results (default: 10)

**Send Email:**
- **Name:** `clawbot_gmail_send`
- **URL:** `http://localhost:8000/gmail/send`
- **Method:** POST
- **Query Parameters:**
  - `user_id` (required)
  - `to` (required): Recipient email
  - `subject` (required): Email subject
  - `body` (required): Email body
  - `body_type` (optional): "plain" or "html" (default: "plain")

#### Calendar Integration

**List Events:**
- **Name:** `clawbot_calendar_list`
- **URL:** `http://localhost:8000/calendar/events`
- **Method:** GET
- **Query Parameters:**
  - `user_id` (required)
  - `calendar_id` (optional): "primary" (default)
  - `max_results` (optional): Number of results

**Create Event:**
- **Name:** `clawbot_calendar_create`
- **URL:** `http://localhost:8000/calendar/events`
- **Method:** POST
- **Query Parameters:**
  - `user_id` (required)
  - `summary` (required): Event title
  - `start_time` (required): ISO format (e.g., "2024-01-15T10:00:00Z")
  - `end_time` (required): ISO format
  - `description` (optional)
  - `location` (optional)
  - `attendees` (optional): Comma-separated emails
  - `add_meet_link` (optional): `true` to add a Google Meet video call link to the event

#### Memory Integration

**Store Memory:**
- **Name:** `clawbot_memory_store`
- **URL:** `http://localhost:8000/memory/store`
- **Method:** POST
- **Query Parameters:**
  - `user_id` (required)
  - `content` (required): Memory content
  - `role` (optional): "user", "assistant", "system" (default: "user")
  - `thread_id` (optional): Conversation thread ID
  - `importance` (optional): 0.0-1.0 (default: 0.5)
  - `tags` (optional): Comma-separated tags

**Get Daily Context:**
- **Name:** `clawbot_memory_daily`
- **URL:** `http://localhost:8000/memory/daily`
- **Method:** GET
- **Query Parameters:**
  - `user_id` (required)
  - `thread_id` (optional)
  - `include_summary` (optional): true/false (default: true)

**Get Long-term Summary:**
- **Name:** `clawbot_memory_longterm`
- **URL:** `http://localhost:8000/memory/long-term/summary`
- **Method:** GET
- **Query Parameters:**
  - `user_id` (required)
  - `days` (optional): Days to summarize (default: 30)

### Method 2: Direct HTTP Calls from OpenClaw

If OpenClaw supports making HTTP requests, you can call Clawbot directly:

```python
# Example: Store a memory after user interaction
import requests

def store_conversation_memory(user_id, user_message, assistant_response):
    # Store user message
    requests.post(
        "http://localhost:8000/memory/store",
        params={
            "user_id": user_id,
            "content": user_message,
            "role": "user",
            "importance": 0.5
        }
    )
    
    # Store assistant response
    requests.post(
        "http://localhost:8000/memory/store",
        params={
            "user_id": user_id,
            "content": assistant_response,
            "role": "assistant",
            "importance": 0.5
        }
    )

# Example: Get context before responding
def get_context_for_response(user_id):
    # Get today's context
    daily = requests.get(
        "http://localhost:8000/memory/daily",
        params={"user_id": user_id, "include_summary": True}
    ).json()
    
    # Get long-term summary
    longterm = requests.get(
        "http://localhost:8000/memory/long-term/summary",
        params={"user_id": user_id, "days": 30}
    ).json()
    
    return {
        "daily_summary": daily.get("summary", ""),
        "longterm_summary": longterm.get("context_summary", ""),
        "user_preferences": longterm.get("user_preferences", {})
    }
```

## Workflow Examples

### Example 1: Conversation with Memory

```python
# Before generating response
context = get_context_for_response(user_id)

# Inject context into prompt
prompt = f"""
User Profile: {context['longterm_summary']}
Today's Context: {context['daily_summary']}
User Preferences: {context['user_preferences']}

User: {user_message}
Assistant:
"""

# Generate response
response = generate_response(prompt)

# Store interaction
store_conversation_memory(user_id, user_message, response)
```

### Example 2: Gmail Integration

```python
# List unread emails
response = requests.get(
    "http://localhost:8000/gmail/messages",
    params={
        "user_id": user_id,
        "query": "is:unread",
        "max_results": 5
    }
)

emails = response.json()["messages"]

# Summarize for user
for email in emails:
    email_details = requests.get(
        f"http://localhost:8000/gmail/messages/{email['id']}",
        params={"user_id": user_id}
    ).json()
    
    print(f"From: {email_details['from']}")
    print(f"Subject: {email_details['subject']}")
    print(f"Snippet: {email_details['snippet']}")
```

### Example 3: Calendar Integration

```python
# Get today's events
today = datetime.now().isoformat() + "Z"
tomorrow = (datetime.now() + timedelta(days=1)).isoformat() + "Z"

events = requests.get(
    "http://localhost:8000/calendar/events",
    params={
        "user_id": user_id,
        "time_min": today,
        "time_max": tomorrow,
        "max_results": 10
    }
).json()

# Create new event
requests.post(
    "http://localhost:8000/calendar/events",
    params={
        "user_id": user_id,
        "summary": "Meeting with team",
        "start_time": "2024-01-15T10:00:00Z",
        "end_time": "2024-01-15T11:00:00Z",
        "attendees": "colleague@example.com"
    }
)
```

## Authentication Flow

### First Time Setup

1. **Get Authorization URL:**
   ```bash
   curl "http://localhost:8000/auth/authorize?user_id=your_user_id"
   ```

2. **Open URL in Browser:**
   - Grant permissions to Gmail, Calendar, etc.
   - You'll be redirected to callback URL

3. **Handle Callback:**
   - The callback URL will contain an authorization code
   - Clawbot automatically exchanges it for tokens
   - Tokens are cached locally

### Subsequent Use

- Tokens are automatically refreshed when needed
- No need to re-authenticate unless tokens are revoked
- Check auth status: `GET /auth/status/{user_id}`

## Memory Best Practices

### Store Important Information

```python
# Store user preferences with high importance
requests.post(
    "http://localhost:8000/memory/long-term/important",
    params={
        "user_id": user_id,
        "content": "User prefers morning meetings before 10 AM",
        "category": "preference"
    }
)
```

### Retrieve Context Before Responses

```python
# Get today's context
daily_context = requests.get(
    "http://localhost:8000/memory/daily",
    params={"user_id": user_id}
).json()

# Use in prompt
context_summary = daily_context.get("summary", "")
```

### Search Past Conversations

```python
# Search for relevant memories
results = requests.get(
    "http://localhost:8000/memory/search",
    params={
        "user_id": user_id,
        "query": "meeting preferences",
        "days": 30,
        "limit": 5
    }
).json()
```

## Testing Integration

### Test Script

Create `test_integration.py`:

```python
import requests

BASE_URL = "http://localhost:8000"
USER_ID = "test_user"

# Test health
response = requests.get(f"{BASE_URL}/health")
print("Health:", response.json())

# Test memory storage
response = requests.post(
    f"{BASE_URL}/memory/store",
    params={
        "user_id": USER_ID,
        "content": "Test memory",
        "importance": 0.8
    }
)
print("Memory stored:", response.json())

# Test memory retrieval
response = requests.get(
    f"{BASE_URL}/memory/daily",
    params={"user_id": USER_ID}
)
print("Daily context:", response.json())
```

Run:
```bash
python test_integration.py
```

## Troubleshooting

### Connection Refused

- Make sure Clawbot is running: `curl http://localhost:8000/health`
- Check port 8000 is not blocked by firewall
- Verify OpenClaw can reach localhost

### Authentication Errors

- Complete OAuth flow first
- Check tokens are cached: `GET /auth/status/{user_id}`
- Re-authenticate if needed

### Memory Not Persisting

- Check `.memory_store/` directory exists
- Verify file permissions
- Check disk space

## Next Steps

1. ✅ Start Clawbot locally
2. ✅ Complete OAuth authentication
3. ✅ Configure OpenClaw to use Clawbot endpoints
4. ✅ Test integrations
5. ✅ Start using in your workflows!
