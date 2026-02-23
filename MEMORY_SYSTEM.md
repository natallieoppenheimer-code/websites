# Clawbot Memory System

Comprehensive memory management system for OpenClaw with daily context windows and long-term memory.

## Overview

The memory system provides:
- **Daily Context**: Track and retrieve today's conversations and interactions
- **Long-term Memory**: Store and recall important information over extended periods
- **Conversation History**: Maintain context across multiple sessions
- **User Profiles**: Build comprehensive user understanding over time

## Architecture

### Storage Backends

1. **File-based** (Default)
   - Stores memories in `.memory_store/` directory
   - JSONL format (one memory per line)
   - Suitable for single-instance deployments

2. **Redis** (Recommended for production)
   - Uses Redis lists for efficient storage
   - Supports multi-instance deployments
   - Automatic expiration (90 days default)
   - Configure via `TOKEN_CACHE_TYPE=redis` in `.env`

### Memory Structure

Each memory entry contains:
- `id`: Unique identifier
- `user_id`: User identifier
- `thread_id`: Optional conversation thread ID
- `content`: Memory content/text
- `role`: "user", "assistant", or "system"
- `timestamp`: Unix timestamp
- `metadata`: Additional JSON metadata
- `tags`: List of tags for categorization
- `importance`: Score from 0.0 to 1.0

## API Endpoints

### Store Memory

```bash
POST /memory/store
```

Store a new memory entry.

**Parameters:**
- `user_id` (required): User ID
- `content` (required): Memory content
- `role` (optional): "user", "assistant", or "system" (default: "user")
- `thread_id` (optional): Thread ID for conversation grouping
- `importance` (optional): Importance score 0.0-1.0 (default: 0.5)
- `tags` (optional): Comma-separated tags
- `metadata` (optional): JSON metadata string

**Example:**
```bash
curl -X POST "http://localhost:8000/memory/store?user_id=user123&content=User%20prefers%20morning%20meetings&importance=0.8&tags=preference,schedule"
```

### Query Memories

```bash
POST /memory/query
```

Query memories with filters.

**Request Body:**
```json
{
  "user_id": "user123",
  "thread_id": "thread456",
  "start_time": 1234567890.0,
  "end_time": 1234567890.0,
  "tags": ["important"],
  "min_importance": 0.7,
  "limit": 50,
  "role": "user"
}
```

### Daily Context

#### Get Today's Context

```bash
GET /memory/daily
```

Retrieve today's context with optional summary.

**Parameters:**
- `user_id` (required): User ID
- `thread_id` (optional): Thread ID
- `include_summary` (optional): Include daily summary (default: true)

**Example:**
```bash
curl "http://localhost:8000/memory/daily?user_id=user123&include_summary=true"
```

**Response:**
```json
{
  "date": "2024-01-15",
  "user_id": "user123",
  "memory_count": 25,
  "summary": "Key events: 3 important interactions. User interactions: 15 messages. Topics: meeting, email, calendar",
  "memories": [...]
}
```

#### Add to Daily Context

```bash
GET /memory/daily/add
```

Add an entry to today's context.

**Parameters:**
- `user_id` (required): User ID
- `content` (required): Content to add
- `role` (optional): Role (default: "user")
- `thread_id` (optional): Thread ID
- `importance` (optional): Importance score
- `tags` (optional): Comma-separated tags

#### Get Context Window

```bash
GET /memory/context-window
```

Get context for multiple days (up to 30 days).

**Parameters:**
- `user_id` (required): User ID
- `days` (optional): Number of days (default: 7, max: 30)
- `thread_id` (optional): Thread ID

**Example:**
```bash
curl "http://localhost:8000/memory/context-window?user_id=user123&days=7"
```

### Conversation Summary

```bash
GET /memory/conversation-summary
```

Get summary of recent conversation.

**Parameters:**
- `user_id` (required): User ID
- `thread_id` (optional): Thread ID
- `hours` (optional): Hours to look back (default: 24, max: 168)

**Response:**
```json
{
  "user_id": "user123",
  "time_window_hours": 24,
  "total_exchanges": 15,
  "user_messages": 8,
  "assistant_messages": 7,
  "summary": "User: I need to schedule a meeting...",
  "topics": ["meeting", "calendar"],
  "key_points": [...]
}
```

### Long-term Memory

#### Get Long-term Summary

```bash
GET /memory/long-term/summary
```

Create a summary of long-term context (up to 365 days).

**Parameters:**
- `user_id` (required): User ID
- `thread_id` (optional): Thread ID
- `days` (optional): Days to summarize (default: 30, max: 365)

**Response:**
```json
{
  "user_id": "user123",
  "period_days": 30,
  "total_memories": 250,
  "patterns": {
    "most_active_hour": 14,
    "days_with_activity": 20,
    "role_distribution": {"user": 120, "assistant": 130}
  },
  "frequent_topics": ["meeting", "email", "calendar"],
  "important_events": [...],
  "user_preferences": {"timezone": "PST", "meeting_duration": "30min"},
  "context_summary": "..."
}
```

#### Get User Profile

```bash
GET /memory/long-term/profile
```

Get comprehensive user profile.

**Parameters:**
- `user_id` (required): User ID
- `include_recent` (optional): Include only recent memories (default: true)

**Response:**
```json
{
  "user_id": "user123",
  "total_interactions": 500,
  "preferences": {
    "timezone": "PST",
    "meeting_duration": "30min",
    "pref:email_format": "html"
  },
  "common_topics": ["meeting", "email", "calendar"],
  "interaction_patterns": {...},
  "key_context": [...],
  "last_updated": "2024-01-15T10:30:00"
}
```

#### Store Important Memory

```bash
POST /memory/long-term/important
```

Store an important long-term memory (high importance).

**Parameters:**
- `user_id` (required): User ID
- `content` (required): Important memory content
- `category` (required): Category/tag
- `thread_id` (optional): Thread ID
- `metadata` (optional): JSON metadata

**Example:**
```bash
curl -X POST "http://localhost:8000/memory/long-term/important?user_id=user123&content=User%20is%20allergic%20to%20peanuts&category=health"
```

### Search Memories

```bash
GET /memory/search
```

Search memories by content.

**Parameters:**
- `user_id` (required): User ID
- `query` (required): Search query text
- `days` (optional): Limit to last N days
- `thread_id` (optional): Thread ID
- `limit` (optional): Max results (default: 20, max: 100)

**Example:**
```bash
curl "http://localhost:8000/memory/search?user_id=user123&query=meeting&days=7&limit=10"
```

### Clear Memories

```bash
DELETE /memory/clear
```

Clear memories for a user.

**Parameters:**
- `user_id` (required): User ID
- `thread_id` (optional): Clear specific thread
- `older_than_days` (optional): Clear memories older than N days

## Usage Patterns

### For OpenClaw Integration

1. **Store each interaction:**
   ```python
   # When user sends a message
   POST /memory/store
   {
     "user_id": "user123",
     "content": "User message text",
     "role": "user",
     "thread_id": "conversation_123"
   }
   
   # When assistant responds
   POST /memory/store
   {
     "user_id": "user123",
     "content": "Assistant response",
     "role": "assistant",
     "thread_id": "conversation_123"
   }
   ```

2. **Retrieve context before responding:**
   ```python
   # Get today's context
   GET /memory/daily?user_id=user123&thread_id=conversation_123
   
   # Get recent conversation summary
   GET /memory/conversation-summary?user_id=user123&hours=24
   
   # Get long-term context
   GET /memory/long-term/summary?user_id=user123&days=30
   ```

3. **Store important information:**
   ```python
   # Store user preferences
   POST /memory/long-term/important
   {
     "user_id": "user123",
     "content": "User prefers morning meetings",
     "category": "preference"
   }
   ```

### Daily Context Workflow

1. **Start of day**: Retrieve today's context to understand what's already happened
2. **During interactions**: Store each exchange with appropriate importance
3. **End of day**: Generate summary for tomorrow's context

### Long-term Memory Workflow

1. **Periodic summaries**: Create weekly/monthly summaries
2. **User profiles**: Build comprehensive understanding over time
3. **Pattern analysis**: Identify user preferences and patterns
4. **Important events**: Store critical information with high importance

## Best Practices

1. **Importance Scoring:**
   - 0.9-1.0: Critical information (preferences, constraints)
   - 0.7-0.8: Important events (meetings, decisions)
   - 0.5-0.6: Normal interactions
   - 0.0-0.4: Routine/less important

2. **Tagging:**
   - Use consistent tags: `preference`, `meeting`, `email`, `calendar`
   - Prefix preferences: `pref:timezone`, `pref:format`
   - Use categories: `health`, `work`, `personal`

3. **Thread Management:**
   - Use `thread_id` to group related conversations
   - Create new threads for new topics
   - Link related threads via metadata

4. **Storage Optimization:**
   - Use Redis for production (better performance)
   - Set appropriate expiration times
   - Regularly clean old memories if needed

## Configuration

Memory system uses the same storage configuration as token cache:

```env
# File-based (default)
TOKEN_CACHE_TYPE=file
TOKEN_CACHE_PATH=./.token_cache

# Redis-based
TOKEN_CACHE_TYPE=redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0  # Memory uses DB+1 automatically
```

## Performance Considerations

- **File-based**: Good for single instance, slower for large datasets
- **Redis**: Better for multi-instance, faster queries, automatic expiration
- **Query limits**: Default limit is 50, max 1000 per query
- **Daily context**: Optimized for fast retrieval of today's memories
- **Long-term queries**: May be slower for large time ranges

## Integration with OpenClaw

The memory system is designed to work seamlessly with OpenClaw:

1. **Context Injection**: Use daily/long-term context in prompts
2. **Preference Learning**: Store and recall user preferences
3. **Conversation Continuity**: Maintain context across sessions
4. **Personalization**: Build user profiles over time

Example integration:
```python
# Before generating response
context = get_daily_context(user_id)
profile = get_user_profile(user_id)
long_term = get_long_term_summary(user_id, days=30)

# Combine into prompt context
prompt_context = f"""
User Profile: {profile}
Today's Context: {context['summary']}
Long-term Context: {long_term['context_summary']}
"""
```
