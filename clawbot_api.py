"""Clawbot FastAPI application with Google integrations"""
import asyncio
import os
import time
import logging
import httpx
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from clawbot.auth.oauth import GoogleOAuth, get_google_credentials
from clawbot.auth.token_cache import token_cache
from clawbot.integrations.gmail import GmailService
from clawbot.integrations.natalie_email import NatalieEmailService, is_natalie_email
from clawbot.integrations.calendar import CalendarService
from clawbot.integrations.gsuite import GSuiteService
from clawbot.routing.router import AgentRouter, RouteRequest, RouteResponse
from clawbot.memory.memory_store import MemoryStore, MemoryEntry, MemoryQuery
from clawbot.memory.daily_context import DailyContextManager
from clawbot.memory.long_term_memory import LongTermMemory
from clawbot.integrations.voice_note import generate_voice_note
from clawbot.config import settings

load_dotenv()

# Directory for generated voice notes (served at /voice-notes/<id>)
VOICE_NOTES_DIR = Path(__file__).resolve().parent / "voice_notes"

# ── Lead Gen daily scheduler ──────────────────────────────────────────────────

_PST = ZoneInfo("America/Los_Angeles")


def _parse_schedule() -> list[tuple[str, str]]:
    """
    Parse LEAD_GEN_SCHEDULE env var into list of (area, category) pairs.
    Format: "Morgan Hill CA|plumber,Morgan Hill CA|electrician"
    """
    raw = os.getenv("LEAD_GEN_SCHEDULE", "")
    pairs = []
    for token in raw.split(","):
        token = token.strip()
        if "|" in token:
            area, cat = token.split("|", 1)
            pairs.append((area.strip(), cat.strip()))
    return pairs


async def _scheduler_loop() -> None:
    """
    Runs in the background forever.
    At the configured hour:minute (PST) each day, fires the lead-gen pipeline
    for every area+category in LEAD_GEN_SCHEDULE.
    Also logs the next scheduled run time on startup.
    """
    schedule_hour   = int(os.getenv("LEAD_GEN_SCHEDULE_HOUR",   "9"))
    schedule_minute = int(os.getenv("LEAD_GEN_SCHEDULE_MINUTE", "0"))
    pairs           = _parse_schedule()

    if not pairs:
        logger.info("[Scheduler] LEAD_GEN_SCHEDULE is empty — auto-pipeline disabled.")
        return

    logger.info(
        f"[Scheduler] Auto-pipeline enabled. "
        f"Runs daily at {schedule_hour:02d}:{schedule_minute:02d} PST "
        f"for: {pairs}"
    )

    last_run_date = None   # track date so we only fire once per day

    while True:
        now_pst = datetime.now(_PST)
        today   = now_pst.date()

        fire = (
            now_pst.hour   == schedule_hour
            and now_pst.minute == schedule_minute
            and last_run_date  != today
        )

        if fire:
            last_run_date = today
            logger.info(
                f"[Scheduler] Firing pipeline at "
                f"{now_pst.strftime('%Y-%m-%d %H:%M %Z')} — {len(pairs)} campaign(s)"
            )
            from clawbot.integrations.lead_gen.pipeline import run_pipeline
            for area, category in pairs:
                try:
                    logger.info(f"[Scheduler] Running: area='{area}' category='{category}'")
                    summary = await run_pipeline(area=area, category=category)
                    logger.info(f"[Scheduler] Done: {summary}")
                except Exception as exc:
                    logger.error(
                        f"[Scheduler] Pipeline error for '{area}/{category}': {exc}",
                        exc_info=True,
                    )

        await asyncio.sleep(30)   # check every 30 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background scheduler on server startup."""
    task = asyncio.create_task(_scheduler_loop())
    logger.info("[Startup] Lead-gen scheduler started.")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("[Shutdown] Lead-gen scheduler stopped.")


# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Clawbot API",
    description="Google Workspace Integration Bot with Gmail, Calendar, and GSuite",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent router
agent_router = AgentRouter()

# Initialize memory system
memory_store = MemoryStore()
daily_context = DailyContextManager(memory_store)
long_term_memory = LongTermMemory(memory_store)


# ==================== Authentication Endpoints ====================

@app.get("/auth/authorize")
async def get_authorization_url(
    user_id: str = Query(..., description="User ID"),
):
    """Redirect browser directly to Google OAuth consent screen"""
    from fastapi.responses import RedirectResponse
    try:
        oauth = GoogleOAuth()
        # Embed user_id in the state parameter so the callback can retrieve it
        auth_url = oauth.get_authorization_url(state=user_id)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: Optional[str] = Query(None, description="user_id encoded in state by /auth/authorize"),
    user_id: Optional[str] = Query(None, description="Explicit user_id override")
):
    """Handle OAuth callback — Google redirects here via GET with code + state"""
    resolved_user_id = user_id or state
    if not resolved_user_id:
        raise HTTPException(status_code=400, detail="Cannot determine user_id: state and user_id are both missing")
    try:
        oauth = GoogleOAuth()
        oauth.exchange_code_for_token(code, resolved_user_id)
        return {
            "success": True,
            "user_id": resolved_user_id,
            "message": "Authentication successful! Gmail and Calendar are now authorized. You can close this tab."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/status/{user_id}")
async def get_auth_status(user_id: str):
    """Check authentication status for a user"""
    cached_token = token_cache.get_token(user_id)
    if cached_token:
        is_valid = token_cache.is_token_valid(cached_token)
        return {
            "authenticated": True,
            "valid": is_valid,
            "has_refresh_token": bool(cached_token.get('refresh_token'))
        }
    return {"authenticated": False, "valid": False}


@app.post("/auth/refresh/{user_id}")
async def refresh_token(user_id: str):
    """Refresh access token"""
    try:
        oauth = GoogleOAuth()
        refreshed = oauth.refresh_token(user_id)
        if refreshed:
            return {"success": True, "message": "Token refreshed"}
        else:
            raise HTTPException(status_code=401, detail="Unable to refresh token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Gmail / Email Endpoints ====================
# When user_id is natalie@equestrolabs.com we use DreamHost SMTP/IMAP (Natalie).
# Otherwise we use Gmail API.

def _email_service(user_id: str):
    """Return Natalie (DreamHost) or Gmail service for this user_id."""
    if is_natalie_email(user_id):
        return NatalieEmailService(user_id)
    return GmailService(user_id)


@app.get("/gmail/messages")
async def list_gmail_messages(
    user_id: str = Query(..., description="User ID (use natalie@equestrolabs.com for Natalie)"),
    query: str = Query("", description="Gmail search query (e.g. is:unread) or IMAP filter"),
    max_results: int = Query(10, description="Maximum number of results")
):
    """List email messages (Gmail or Natalie DreamHost)"""
    try:
        svc = _email_service(user_id)
        messages = svc.list_messages(query=query, max_results=max_results)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gmail/messages/{message_id}")
async def get_gmail_message(
    message_id: str,
    user_id: str = Query(..., description="User ID")
):
    """Get email message details"""
    try:
        svc = _email_service(user_id)
        message = svc.get_message(message_id)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gmail/send")
async def send_email(
    user_id: str = Query(..., description="User ID (use natalie@equestrolabs.com for Natalie)"),
    to: str = Query(..., description="Recipient email"),
    subject: str = Query(..., description="Email subject"),
    body: str = Query(..., description="Email body"),
    body_type: str = Query("plain", description="Body type: plain or html")
):
    """Send an email (via Gmail API or Natalie DreamHost SMTP)"""
    try:
        svc = _email_service(user_id)
        result = svc.send_message(to, subject, body, body_type)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gmail/labels")
async def get_gmail_labels(user_id: str = Query(..., description="User ID")):
    """Get email labels (Gmail labels or INBOX for Natalie)"""
    try:
        svc = _email_service(user_id)
        labels = svc.get_labels()
        return {"labels": labels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Calendar Endpoints ====================

@app.get("/calendar/calendars")
async def list_calendars(user_id: str = Query(..., description="User ID")):
    """List all calendars"""
    try:
        calendar = CalendarService(user_id)
        calendars = calendar.list_calendars()
        return {"calendars": calendars}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calendar/events")
async def list_calendar_events(
    user_id: str = Query(..., description="User ID"),
    calendar_id: str = Query("primary", description="Calendar ID"),
    max_results: int = Query(10, description="Maximum number of results"),
    time_min: Optional[str] = Query(None, description="Start time (ISO format)"),
    time_max: Optional[str] = Query(None, description="End time (ISO format)")
):
    """List calendar events"""
    try:
        calendar = CalendarService(user_id)
        time_min_dt = datetime.fromisoformat(time_min.replace('Z', '+00:00')) if time_min else None
        time_max_dt = datetime.fromisoformat(time_max.replace('Z', '+00:00')) if time_max else None
        events = calendar.list_events(
            calendar_id=calendar_id,
            time_min=time_min_dt,
            time_max=time_max_dt,
            max_results=max_results
        )
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calendar/events")
async def create_calendar_event(
    user_id: str = Query(..., description="User ID"),
    summary: str = Query(..., description="Event summary"),
    start_time: str = Query(..., description="Start time (ISO format)"),
    end_time: str = Query(..., description="End time (ISO format)"),
    description: Optional[str] = Query(None, description="Event description"),
    location: Optional[str] = Query(None, description="Event location"),
    calendar_id: str = Query("primary", description="Calendar ID"),
    attendees: Optional[str] = Query(None, description="Comma-separated attendee emails"),
    add_meet_link: bool = Query(False, description="Add Google Meet video call link to the event")
):
    """Create a calendar event. Set add_meet_link=true for a video call (Google Meet)."""
    try:
        calendar = CalendarService(user_id)
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        attendee_list = attendees.split(',') if attendees else None
        event = calendar.create_event(
            summary=summary,
            start_time=start_dt,
            end_time=end_dt,
            description=description,
            location=location,
            attendees=attendee_list,
            calendar_id=calendar_id,
            add_meet_link=add_meet_link
        )
        return {"success": True, "event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calendar/events/{event_id}")
async def get_calendar_event(
    event_id: str,
    user_id: str = Query(..., description="User ID"),
    calendar_id: str = Query("primary", description="Calendar ID")
):
    """Get calendar event details"""
    try:
        calendar = CalendarService(user_id)
        event = calendar.get_event(event_id, calendar_id)
        return {"event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/calendar/events/{event_id}")
async def delete_calendar_event(
    event_id: str,
    user_id: str = Query(..., description="User ID"),
    calendar_id: str = Query("primary", description="Calendar ID")
):
    """Delete a calendar event"""
    try:
        calendar = CalendarService(user_id)
        success = calendar.delete_event(event_id, calendar_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GSuite Endpoints ====================

@app.get("/gsuite/users")
async def list_gsuite_users(
    user_id: str = Query(..., description="User ID"),
    domain: Optional[str] = Query(None, description="Domain filter"),
    max_results: int = Query(100, description="Maximum number of results"),
    query: Optional[str] = Query(None, description="Search query")
):
    """List GSuite users"""
    try:
        gsuite = GSuiteService(user_id, domain=domain)
        users = gsuite.list_users(domain=domain, max_results=max_results, query=query)
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gsuite/users/{user_key}")
async def get_gsuite_user(
    user_key: str,
    user_id: str = Query(..., description="User ID")
):
    """Get GSuite user details"""
    try:
        gsuite = GSuiteService(user_id)
        user = gsuite.get_user(user_key)
        return {"user": user}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gsuite/groups")
async def list_gsuite_groups(
    user_id: str = Query(..., description="User ID"),
    domain: Optional[str] = Query(None, description="Domain filter"),
    max_results: int = Query(100, description="Maximum number of results")
):
    """List GSuite groups"""
    try:
        gsuite = GSuiteService(user_id, domain=domain)
        groups = gsuite.list_groups(domain=domain, max_results=max_results)
        return {"groups": groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gsuite/groups/{group_key}/members")
async def list_group_members(
    group_key: str,
    user_id: str = Query(..., description="User ID")
):
    """List members of a GSuite group"""
    try:
        gsuite = GSuiteService(user_id)
        members = gsuite.list_group_members(group_key)
        return {"members": members}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Multi-Agent Routing Endpoints ====================

@app.post("/route", response_model=RouteResponse)
async def route_request(request: RouteRequest):
    """Route request to appropriate agent"""
    try:
        response = agent_router.route(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/register")
async def register_agent(agent: Dict[str, Any]):
    """Register a new agent"""
    try:
        agent_router.register_agent(agent)
        return {"success": True, "message": "Agent registered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def list_agents():
    """List all registered agents"""
    return {"agents": agent_router.list_agents()}


@app.put("/agents/{agent_id}/status")
async def update_agent_status(
    agent_id: str,
    available: Optional[bool] = Query(None),
    current_load: Optional[int] = Query(None)
):
    """Update agent status"""
    try:
        agent_router.update_agent_status(agent_id, available, current_load)
        return {"success": True, "message": "Agent status updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Memory Endpoints ====================

@app.post("/memory/store")
async def store_memory(
    user_id: str = Query(..., description="User ID"),
    content: str = Query(..., description="Memory content"),
    role: str = Query("user", description="Role: user, assistant, system"),
    thread_id: Optional[str] = Query(None, description="Thread ID"),
    importance: float = Query(0.5, ge=0.0, le=1.0, description="Importance score"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    metadata: Optional[str] = Query(None, description="JSON metadata")
):
    """Store a memory entry"""
    try:
        import json as json_lib
        tags_list = tags.split(',') if tags else []
        metadata_dict = json_lib.loads(metadata) if metadata else {}
        
        entry = MemoryEntry(
            id=f"{user_id}_{int(time.time() * 1000)}",
            user_id=user_id,
            thread_id=thread_id,
            content=content,
            role=role,
            timestamp=time.time(),
            metadata=metadata_dict,
            tags=tags_list,
            importance=importance
        )
        
        success = memory_store.store(entry)
        return {"success": success, "entry": entry.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/query")
async def query_memories(query: MemoryQuery):
    """Query memories"""
    try:
        memories = memory_store.retrieve(query)
        return {
            "count": len(memories),
            "memories": [m.dict() for m in memories]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/daily")
async def get_daily_context(
    user_id: str = Query(..., description="User ID"),
    thread_id: Optional[str] = Query(None, description="Thread ID"),
    include_summary: bool = Query(True, description="Include daily summary")
):
    """Get today's context"""
    try:
        context = daily_context.get_today_context(
            user_id=user_id,
            thread_id=thread_id,
            include_summary=include_summary
        )
        return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/daily/add")
async def add_to_daily_context(
    user_id: str = Query(..., description="User ID"),
    content: str = Query(..., description="Content to add"),
    role: str = Query("user", description="Role"),
    thread_id: Optional[str] = Query(None, description="Thread ID"),
    importance: float = Query(0.5, ge=0.0, le=1.0),
    tags: Optional[str] = Query(None, description="Comma-separated tags")
):
    """Add entry to today's context"""
    try:
        tags_list = tags.split(',') if tags else []
        entry = daily_context.add_to_daily_context(
            user_id=user_id,
            content=content,
            role=role,
            thread_id=thread_id,
            importance=importance,
            tags=tags_list
        )
        return {"success": True, "entry": entry.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/context-window")
async def get_context_window(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(7, ge=1, le=30, description="Number of days"),
    thread_id: Optional[str] = Query(None, description="Thread ID")
):
    """Get context window for multiple days"""
    try:
        context = daily_context.get_context_window(
            user_id=user_id,
            days=days,
            thread_id=thread_id
        )
        return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/conversation-summary")
async def get_conversation_summary(
    user_id: str = Query(..., description="User ID"),
    thread_id: Optional[str] = Query(None, description="Thread ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """Get conversation summary"""
    try:
        summary = daily_context.get_conversation_summary(
            user_id=user_id,
            thread_id=thread_id,
            hours=hours
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/long-term/summary")
async def get_long_term_summary(
    user_id: str = Query(..., description="User ID"),
    thread_id: Optional[str] = Query(None, description="Thread ID"),
    days: int = Query(30, ge=1, le=365, description="Days to summarize")
):
    """Get long-term memory summary"""
    try:
        summary = long_term_memory.create_summary(
            user_id=user_id,
            thread_id=thread_id,
            days=days
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/long-term/profile")
async def get_user_profile(
    user_id: str = Query(..., description="User ID"),
    include_recent: bool = Query(True, description="Include only recent memories")
):
    """Get comprehensive user profile"""
    try:
        profile = long_term_memory.get_user_profile(
            user_id=user_id,
            include_recent=include_recent
        )
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/long-term/important")
async def store_important_memory(
    user_id: str = Query(..., description="User ID"),
    content: str = Query(..., description="Important memory content"),
    category: str = Query(..., description="Category/tag"),
    thread_id: Optional[str] = Query(None, description="Thread ID"),
    metadata: Optional[str] = Query(None, description="JSON metadata")
):
    """Store an important long-term memory"""
    try:
        import json as json_lib
        metadata_dict = json_lib.loads(metadata) if metadata else {}
        
        entry = long_term_memory.store_important_memory(
            user_id=user_id,
            content=content,
            category=category,
            thread_id=thread_id,
            metadata=metadata_dict
        )
        return {"success": True, "entry": entry.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/search")
async def search_memories(
    user_id: str = Query(..., description="User ID"),
    query: str = Query(..., description="Search query"),
    days: Optional[int] = Query(None, description="Limit to last N days"),
    thread_id: Optional[str] = Query(None, description="Thread ID"),
    limit: int = Query(20, ge=1, le=100)
):
    """Search memories by content"""
    try:
        results = long_term_memory.search_memories(
            user_id=user_id,
            query_text=query,
            days=days,
            thread_id=thread_id,
            limit=limit
        )
        return {
            "count": len(results),
            "results": [m.dict() for m in results]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memory/clear")
async def clear_memories(
    user_id: str = Query(..., description="User ID"),
    thread_id: Optional[str] = Query(None, description="Thread ID"),
    older_than_days: Optional[int] = Query(None, description="Clear memories older than N days")
):
    """Clear memories for a user"""
    try:
        success = memory_store.clear_user_memories(
            user_id=user_id,
            thread_id=thread_id,
            older_than_days=older_than_days
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SMS Endpoints ====================

class SendSmsRequest(BaseModel):
    phone_number: str = Field(..., description="Recipient phone number in E.164 format, e.g. +15555551234")
    text: str = Field(..., description="SMS message body")
    include_voice_note: bool = Field(
        False,
        description="If true, generate a short female-voice note and append a link in the SMS for realism.",
    )


class TextLinkWebhookPayload(BaseModel):
    secret: Optional[str] = None
    phone_number: Optional[str] = None
    text: Optional[str] = None
    name: Optional[str] = None
    tag: Optional[str] = None
    sim_card_id: Optional[int] = None
    portal: Optional[bool] = None
    timestamp: Optional[int] = None
    textlink_id: Optional[int] = None
    custom_id: Optional[str] = None
    subuser_id: Optional[int] = None


@app.get("/voice-notes/{file_id}", response_class=FileResponse)
async def get_voice_note(file_id: str):
    """Serve a generated voice note MP3 (female voice, for SMS realism)."""
    if not file_id or ".." in file_id or "/" in file_id:
        raise HTTPException(status_code=400, detail="Invalid file id")
    path = VOICE_NOTES_DIR / f"{file_id}.mp3"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Voice note not found")
    return FileResponse(path, media_type="audio/mpeg", filename=f"{file_id}.mp3")


@app.post("/send-sms")
async def send_sms(request: SendSmsRequest):
    """Send an outbound SMS via TextLink API. Optionally include a short voice note link (female voice)."""
    text_to_send = request.text
    if request.include_voice_note and getattr(settings, "ELEVENLABS_API_KEY", None):
        try:
            file_id, _ = await asyncio.to_thread(
                generate_voice_note,
                request.text,
                settings.ELEVENLABS_API_KEY,
                storage_dir=VOICE_NOTES_DIR,
            )
            if file_id:
                base_url = (getattr(settings, "CLAWBOT_BASE_URL", None) or "http://localhost:8000").rstrip("/")
                voice_url = f"{base_url}/voice-notes/{file_id}"
                text_to_send = f"{request.text}\n\nVoice note: {voice_url}"
        except Exception as e:
            logger.warning("Voice note generation failed, sending text only: %s", e)
    logger.warning(f"[send-sms] Sending to {request.phone_number}: {text_to_send[:80]!r}")
    api_key = settings.TEXTLINK_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="TEXTLINK_API_KEY is not configured")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://textlinksms.com/api/send-sms",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "phone_number": request.phone_number,
                    "text": text_to_send,
                },
            )
        data = response.json()
        if response.status_code != 200 or not data.get("ok"):
            raise HTTPException(
                status_code=502,
                detail=f"TextLink error: {data.get('message', response.text)}"
            )
        return {
            "success": True,
            "phone_number": request.phone_number,
            "textlink": {"ok": data.get("ok"), "queued": data.get("queued"), "message": data.get("message"), "sim_card_id": data.get("sim_card_id")},
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach TextLink API: {e}")


@app.post("/webhook/sms/received")
async def sms_received(payload: TextLinkWebhookPayload):
    """
    Handle incoming SMS from TextLink.
    Verifies the secret, stores the message in memory, and forwards it to
    the OpenClaw agent via the gateway hooks endpoint so the agent can reply.
    """
    webhook_secret = settings.TEXTLINK_WEBHOOK_SECRET
    if webhook_secret and payload.secret != webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    sender = payload.phone_number or "unknown"
    text = payload.text or ""
    name = payload.name or sender

    logger.info(f"Incoming SMS from {name} ({sender}): {text!r}")

    # Store the incoming SMS in memory so the agent has context
    try:
        import hashlib
        memory_content = f"Incoming SMS from {name} ({sender}): {text}"
        entry_id = hashlib.md5(f"sms:{sender}:{time.time()}".encode()).hexdigest()
        memory_store.store(
            MemoryEntry(
                id=entry_id,
                user_id="paul",
                content=memory_content,
                role="user",
                importance=0.8,
                tags=["sms", "incoming", sender],
            )
        )
    except Exception as e:
        logger.warning(f"Failed to store SMS in memory: {e}")

    # Forward to an isolated agent via /hooks/agent.
    # Message is plain context only — no commands or keys embedded.
    # The agent uses its workspace (TOOLS.md, SOUL.md) to know how to send SMS replies.
    gateway_url = settings.OPENCLAW_GATEWAY_URL
    hooks_token = settings.OPENCLAW_HOOKS_TOKEN
    agent_message = (
        f"You received an inbound SMS from {name} ({sender}): \"{text}\"\n\n"
        f"You are Natalie — a warm, witty, human sales rep for EquestroLabs (equestrolabs.com). "
        f"EquestroLabs builds AI solutions for SMBs: mobile apps, web apps, big data systems, "
        f"AI strategy consulting, process automation, and 14 AI agent products "
        f"(Social Media Manager, Customer Support, Sales Management, AI Receptionist, SEO, "
        f"Email Marketing, Copywriting, Data Analysis, Business Strategy, E-commerce, "
        f"Recruitment, Virtual Assistant, Personal Assistant, Legal Assistant). "
        f"Stats: 50+ projects, 3x avg ROI, 95% satisfaction. Founder: Chris Cross, Silicon Valley, 3 exits. "
        f"NEVER mention Paul, Paulo, or Borges.\n\n"
        f"Reply rules: be warm, flirty if appropriate, never robotic, never disagree with the customer, "
        f"match their energy, keep it short and conversational. "
        f"NEVER end with '— Natalie' or any sign-off. Do NOT sign your name at the end. Ever. "
        f"If they ask about pricing, say it depends on scope and offer a free discovery call. "
        f"Always close toward a next step.\n\n"
        f"Send your SMS reply via exec (optionally add a short voice note for realism, female voice): "
        f"curl -s -X POST http://localhost:8000/send-sms "
        f"-H 'Content-Type: application/json' "
        f"-d '{{\"phone_number\":\"{sender}\",\"text\":\"YOUR_REPLY\",\"include_voice_note\":true}}'"
    )
    # Each SMS gets its own unique session key to prevent queue contention
    import hashlib
    session_suffix = hashlib.md5(f"{sender}:{time.time()}".encode()).hexdigest()[:8]
    session_key = f"hook:sms:{session_suffix}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{gateway_url}/hooks/agent",
                json={
                    "message": agent_message,
                    "name": "SMS",
                    "deliver": False,
                    "sessionKey": session_key,
                    "timeoutSeconds": 60,
                },
                headers={"Authorization": f"Bearer {hooks_token}"},
            )
    except Exception as e:
        logger.warning(f"Failed to forward SMS to OpenClaw gateway: {e}")

    return {"ok": True}


@app.post("/webhook/sms/sent")
async def sms_sent(payload: TextLinkWebhookPayload):
    """Acknowledge sent-message webhook from TextLink"""
    webhook_secret = settings.TEXTLINK_WEBHOOK_SECRET
    if webhook_secret and payload.secret != webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    return {"ok": True}


@app.post("/webhook/sms/failed")
async def sms_failed(payload: TextLinkWebhookPayload):
    """Handle failed-message webhook from TextLink"""
    webhook_secret = settings.TEXTLINK_WEBHOOK_SECRET
    if webhook_secret and payload.secret != webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    logger.error(
        f"TextLink delivery failure: to={payload.phone_number} "
        f"text={payload.text!r} id={payload.textlink_id}"
    )
    return {"ok": True}


# ==================== Lead Generation Endpoints ====================

_DASHBOARD_PATH = Path(__file__).parent / "clawbot" / "integrations" / "lead_gen" / "dashboard.html"


@app.get("/leads/dashboard", response_class=HTMLResponse, tags=["Lead Gen"])
async def leads_dashboard():
    """Serve the lead generation web dashboard."""
    if not _DASHBOARD_PATH.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return HTMLResponse(content=_DASHBOARD_PATH.read_text())


@app.get("/leads/scheduler/status", tags=["Lead Gen"])
async def scheduler_status():
    """Return the current scheduler configuration and next scheduled run time."""
    from zoneinfo import ZoneInfo
    pst = ZoneInfo("America/Los_Angeles")
    now_pst = datetime.now(pst)
    schedule_hour   = int(os.getenv("LEAD_GEN_SCHEDULE_HOUR", "9"))
    schedule_minute = int(os.getenv("LEAD_GEN_SCHEDULE_MINUTE", "0"))
    pairs           = _parse_schedule()

    from datetime import timedelta
    next_run = now_pst.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
    if next_run <= now_pst:
        next_run += timedelta(days=1)

    return {
        "enabled":        bool(pairs),
        "campaigns":      [{"area": a, "category": c} for a, c in pairs],
        "schedule":       f"Daily at {schedule_hour:02d}:{schedule_minute:02d} PST",
        "now_pst":        now_pst.strftime("%Y-%m-%d %H:%M %Z"),
        "next_run_pst":   next_run.strftime("%Y-%m-%d %H:%M %Z"),
    }


class LeadInjectBody(BaseModel):
    """Body for injecting one test lead (E2E)."""
    area: str = Field(..., description="Area, e.g. 'Morgan Hill CA'")
    category: str = Field(..., description="Category, e.g. 'plumber'")
    business_name: str = Field("E2E Test Lead", description="Business name")
    biz_phone: str = Field("5550000000", description="Biz phone (use real for live Touch 1)")


@app.post("/leads/inject", tags=["Lead Gen"])
async def inject_one_lead(payload: LeadInjectBody):
    """
    Inject one test lead into the Leads sheet (for E2E). Then call POST /leads/run/sync
    with same area/category and max_to_process=1 (and dry_run=true to skip real send).
    """
    try:
        from clawbot.integrations.lead_gen import sheets as sh
        sh.ensure_sheet()
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        row = {
            "ID": "",
            "Business Name": payload.business_name,
            "Category": payload.category,
            "Area": payload.area,
            "Biz Phone": payload.biz_phone,
            "Website": "",
            "Biz Address": "",
            "Owner Name": "",
            "Owner City": "",
            "Owner State": "",
            "Best Phone": "",
            "Best Email": "",
            "Status": "sourced",
            "SMS Sent": "NO",
            "Email Sent": "NO",
            "Date Added": today,
            "Notes": "E2E test lead",
            "Drip Step": "0",
            "Next Contact": "",
        }
        row_index = sh.append_lead(row)
        return {"ok": True, "row_index": row_index, "message": f"Injected '{payload.business_name}'. Run pipeline with max_to_process=1."}
    except Exception as exc:
        logger.error(f"[leads/inject] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/leads", tags=["Lead Gen"])
async def list_leads(
    sheet_tab: Optional[str] = Query(None, description="Sheet tab name, e.g. 'Leads - Electrician South Bay'. Omit for default 'Leads'."),
):
    """Return all leads from Google Sheets as JSON. Use sheet_tab to read campaign tabs."""
    try:
        from clawbot.integrations.lead_gen import sheets as sh
        if sheet_tab:
            with sh.use_sheet_tab(sheet_tab):
                leads = sh.get_all_leads()
        else:
            leads = sh.get_all_leads()
        return leads
    except Exception as exc:
        logger.error(f"[leads] Failed to read Sheets: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/leads/run", tags=["Lead Gen"])
async def run_leads(
    background_tasks: BackgroundTasks,
    area: str = Query(..., description="Geographic area, e.g. 'Morgan Hill CA'"),
    category: str = Query(..., description="Business category, e.g. 'plumber'"),
):
    """
    Trigger the full lead generation pipeline:
    source → BizFile → people search → outreach (SMS + email).
    Runs in the background; returns immediately with a job acknowledgement.
    The pipeline result is logged to clawbot.log.
    """
    async def _run():
        try:
            from clawbot.integrations.lead_gen.pipeline import run_pipeline
            summary = await run_pipeline(area=area, category=category)
            logger.info(f"[leads/run] Pipeline finished: {summary}")
        except Exception as exc:
            logger.error(f"[leads/run] Pipeline error: {exc}", exc_info=True)

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "area": area,
        "category": category,
        "message": "Pipeline is running in the background. Refresh /leads to see results.",
    }


@app.post("/leads/run/sync", tags=["Lead Gen"])
async def run_leads_sync(
    area: str = Query(..., description="Geographic area, e.g. 'Morgan Hill CA'"),
    category: str = Query(..., description="Business category, e.g. 'plumber'"),
    max_to_process: Optional[int] = Query(None, description="If set, only process this many leads (e.g. 1 for E2E test)"),
    dry_run: bool = Query(False, description="If true, set LEAD_GEN_DRY_RUN so no real SMS/email sent"),
):
    """
    Synchronous version of the pipeline — waits for completion and returns the summary.
    Use this from the dashboard for immediate feedback.
    For E2E test: max_to_process=1&dry_run=true (and set LEAD_GEN_DRY_RUN in env or we set it here).
    """
    if dry_run:
        os.environ["LEAD_GEN_DRY_RUN"] = "1"
    try:
        from clawbot.integrations.lead_gen.pipeline import run_pipeline
        summary = await run_pipeline(area=area, category=category, max_to_process=max_to_process)
        return summary
    except Exception as exc:
        logger.error(f"[leads/run/sync] Pipeline error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/leads/campaign/run", tags=["Lead Gen"])
async def run_campaign_leads(
    background_tasks: BackgroundTasks,
    campaign_id: str = Query(
        "electrician_morgan_hill_south_bay",
        description="Campaign ID, e.g. electrician_morgan_hill_south_bay",
    ),
    skip_time_check: bool = Query(
        False,
        description="If true, run even outside 6 AM–11 PM PST (e.g. for testing)",
    ),
):
    """
    Run the electrician campaign for Morgan Hill + South Bay CA.
    Same strategy: source leads → enrich → Touch 1 SMS; drip Touch 2 (Day 3), Touch 3 email (Day 7).
    Only runs when current time is 6 AM–11 PM PST unless skip_time_check=true.
    Runs in background; returns immediately.
    """
    async def _run():
        try:
            from clawbot.integrations.lead_gen.campaigns import run_campaign
            result = await run_campaign(campaign_id, skip_time_check=skip_time_check)
            logger.info(f"[leads/campaign/run] Finished: {result.get('status')} — {result}")
        except Exception as exc:
            logger.error(f"[leads/campaign/run] Error: {exc}", exc_info=True)

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "campaign_id": campaign_id,
        "message": "Campaign running in background. Runs only 6 AM–11 PM PST. Refresh /leads for results.",
    }


@app.post("/leads/campaign/run/sync", tags=["Lead Gen"])
async def run_campaign_leads_sync(
    campaign_id: str = Query(
        "electrician_morgan_hill_south_bay",
        description="Campaign ID",
    ),
    skip_time_check: bool = Query(False, description="Run outside 6 AM–11 PM PST"),
):
    """
    Run the electrician Morgan Hill + South Bay campaign synchronously.
    Returns summary or skip reason (e.g. outside send window).
    """
    try:
        from clawbot.integrations.lead_gen.campaigns import run_campaign
        return await run_campaign(campaign_id, skip_time_check=skip_time_check)
    except Exception as exc:
        logger.error(f"[leads/campaign/run/sync] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ==================== Website Audit Endpoints ====================

_AUDIT_DASHBOARD_PATH = Path(__file__).parent / "clawbot" / "integrations" / "website_audit" / "audit_dashboard.html"
_DEMOS_DIR = Path(__file__).parent / "clawbot" / "integrations" / "website_audit" / "demos"
_RENDER_BASE = os.getenv("RENDER_EXTERNAL_URL", "https://websites-natalie.onrender.com")


@app.get("/audit/dashboard", response_class=HTMLResponse, tags=["Website Audit"])
async def audit_dashboard():
    """Serve the website/SEO audit PoC dashboard."""
    if not _AUDIT_DASHBOARD_PATH.exists():
        raise HTTPException(status_code=404, detail="Audit dashboard not found")
    return HTMLResponse(content=_AUDIT_DASHBOARD_PATH.read_text())


@app.get("/demos", tags=["Website Demos"])
async def list_demos():
    """
    List all available rebuilt demo websites.
    Sources from both the Website Customers sheet (slugs) and any HTML
    files already written to the demos directory.
    """
    items = []
    seen: set = set()

    # 1. Sheet-registered demos
    try:
        from clawbot.integrations.website_customers import list_customers
        for c in list_customers():
            slug = c.get("Slug", "").strip()
            if slug and slug not in seen:
                items.append({
                    "slug": slug,
                    "business_name": c.get("Business Name", ""),
                    "url": f"{_RENDER_BASE}/demos/{slug}",
                    "status": c.get("Status", ""),
                    "audit_score": c.get("Audit Score", ""),
                })
                seen.add(slug)
    except Exception:
        pass

    # 2. Also surface any HTML files in the demos dir not in the sheet
    _DEMOS_DIR.mkdir(parents=True, exist_ok=True)
    for f in sorted(_DEMOS_DIR.glob("*.html")):
        slug = f.stem.replace("_", "-")
        if slug not in seen:
            items.append({"slug": slug, "business_name": slug, "url": f"{_RENDER_BASE}/demos/{slug}", "status": "local"})
            seen.add(slug)

    return {"demos": items, "total": len(items)}


@app.get("/demos/{slug}", response_class=HTMLResponse, tags=["Website Demos"])
async def serve_demo(slug: str):
    """
    Serve a rebuilt, SEO-optimised demo website by slug.

    Strategy (in order):
      1. Look for a pre-generated HTML file on disk (demos/<slug>.html or demos/<slug_underscored>.html)
      2. Look up the customer in the sheet and regenerate from their stored data
      3. 404
    """
    from clawbot.integrations.website_audit.generator import generate_demo_html, slugify

    _DEMOS_DIR.mkdir(parents=True, exist_ok=True)

    # Try exact filename match (slug with dashes or underscores)
    for candidate in [slug, slug.replace("-", "_")]:
        path = _DEMOS_DIR / f"{candidate}.html"
        if path.exists():
            return HTMLResponse(content=path.read_text())

    # Try to regenerate from sheet data
    try:
        from clawbot.integrations.website_customers import get_customer_by_slug
        customer = get_customer_by_slug(slug)
        if customer:
            html = generate_demo_html(
                business_name=customer.get("Business Name", slug),
                business_phone=customer.get("Business Phone", customer.get("Contact Phone", "")),
                service_area=customer.get("Service Area", ""),
                current_site_url=customer.get("Current Site URL", ""),
                category=customer.get("Category", ""),
                slug=slug,
                render_base_url=_RENDER_BASE,
            )
            # Cache to disk for next request
            (path := _DEMOS_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
            return HTMLResponse(content=html)
    except Exception as exc:
        logger.warning("[demos/%s] Sheet lookup failed: %s", slug, exc)

    raise HTTPException(
        status_code=404,
        detail=f"No demo found for '{slug}'. Use POST /demos/generate to create one.",
    )


@app.post("/audit/run", tags=["Website Audit"])
async def audit_run(url: str = Query(..., description="URL of the website to audit")):
    """
    Run a website/SEO audit on the given URL.
    Returns findings, solutions, and summary (including 'where we can get you').
    """
    try:
        from clawbot.integrations.website_audit import run_audit, report_to_dict
        report = await run_audit(url)
        return report_to_dict(report)
    except Exception as exc:
        logger.error(f"[audit/run] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/audit", tags=["Website Audit"])
async def audit_get(url: str = Query(..., description="URL of the website to audit")):
    """Run a website/SEO audit (GET). Same as POST /audit/run."""
    try:
        from clawbot.integrations.website_audit import run_audit, report_to_dict
        report = await run_audit(url)
        return report_to_dict(report)
    except Exception as exc:
        logger.error(f"[audit] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ==================== Website Customers (registry for "art of the possible") ====================

class WebsiteCustomerRegister(BaseModel):
    """Payload for registering a prospect who wants to see their SEO alternative."""
    business_name: str = Field(..., description="Business or site name")
    contact_email: str = Field(..., description="Contact email")
    current_site_url: str = Field(..., description="URL that was audited")
    contact_phone: Optional[str] = Field(None, description="Optional contact phone")
    business_phone: Optional[str] = Field(None, description="Main business phone (shown on demo site)")
    service_area: Optional[str] = Field(None, description="Service area, e.g. 'Morgan Hill & Gilroy, CA'")
    category: Optional[str] = Field(None, description="Business category, e.g. 'plumber'")
    audit_score: Optional[float] = Field(None, description="Audit score 0–100 if just audited")
    audit_findings_count: Optional[int] = Field(None, description="Number of findings if just audited")


class DemoGenerateRequest(BaseModel):
    """Payload for generating (or regenerating) a demo site for any business."""
    business_name: str = Field(..., description="Business name")
    business_phone: str = Field(..., description="Primary phone number")
    service_area: str = Field(..., description="Service area, e.g. 'Morgan Hill & Gilroy, CA'")
    current_site_url: Optional[str] = Field("", description="Their current website URL (for comparison banner)")
    category: Optional[str] = Field("", description="Business category, e.g. 'plumber', 'electrician'")
    services: Optional[List[str]] = Field(None, description="Override service list (up to 6)")
    tagline: Optional[str] = Field("", description="Custom tagline / hero subtext")


@app.post("/demos/generate", tags=["Website Demos"])
async def generate_demo(payload: DemoGenerateRequest):
    """
    Generate (or regenerate) a demo site for any business.

    Returns the slug and the shareable URL immediately.
    The HTML is cached to disk so subsequent GET /demos/{slug} requests are instant.
    """
    from clawbot.integrations.website_audit.generator import generate_demo_html, slugify

    slug = slugify(payload.business_name)
    html = generate_demo_html(
        business_name=payload.business_name,
        business_phone=payload.business_phone,
        service_area=payload.service_area,
        current_site_url=payload.current_site_url or "",
        category=payload.category or "",
        services=payload.services,
        tagline=payload.tagline or "",
        slug=slug,
        render_base_url=_RENDER_BASE,
    )
    _DEMOS_DIR.mkdir(parents=True, exist_ok=True)
    (_DEMOS_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
    demo_url = f"{_RENDER_BASE}/demos/{slug}"
    logger.info("[demos/generate] Built demo for '%s' → %s", payload.business_name, demo_url)
    return {
        "ok": True,
        "slug": slug,
        "demo_url": demo_url,
        "message": f"Demo site ready for {payload.business_name}",
    }


@app.post("/website-customers/register", tags=["Website Customers"])
async def website_customers_register(payload: WebsiteCustomerRegister):
    """
    Register a prospect AND auto-generate their demo site immediately.
    Returns the shareable demo URL right away.
    """
    try:
        from clawbot.integrations.website_customers import register_customer
        row = register_customer(
            business_name=payload.business_name,
            contact_email=payload.contact_email,
            current_site_url=payload.current_site_url,
            contact_phone=payload.contact_phone,
            business_phone=payload.business_phone,
            service_area=payload.service_area,
            category=payload.category,
            audit_score=payload.audit_score,
            audit_findings_count=payload.audit_findings_count,
        )
        demo_url = row.get("Alternative Site URL", "")
        return {
            "ok": True,
            "id": row["ID"],
            "slug": row.get("Slug", ""),
            "demo_url": demo_url,
            "message": f"Demo site built and ready to share: {demo_url}",
        }
    except Exception as exc:
        logger.error(f"[website-customers/register] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/website-customers", tags=["Website Customers"])
async def website_customers_list():
    """List all website customers (prospects and those with demo/live sites)."""
    try:
        from clawbot.integrations.website_customers import list_customers
        return list_customers()
    except Exception as exc:
        logger.error(f"[website-customers] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


class WebsiteCustomerUpdate(BaseModel):
    """Payload for updating a customer (status, alternative site URL)."""
    status: Optional[str] = Field(None, description="prospect | demo_built | live | lost")
    alternative_site_url: Optional[str] = Field(None, description="URL of the rebuilt SEO demo site")
    notes: Optional[str] = Field(None, description="Internal notes")


@app.patch("/website-customers/{customer_id}", tags=["Website Customers"])
async def website_customers_update(customer_id: str, payload: WebsiteCustomerUpdate):
    """Update a website customer (e.g. set status to demo_built and add Alternative Site URL)."""
    try:
        from clawbot.integrations.website_customers import update_customer
        updated = update_customer(
            customer_id=customer_id,
            status=payload.status,
            alternative_site_url=payload.alternative_site_url,
            notes=payload.notes,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"ok": True, "id": customer_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[website-customers/update] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ==================== Health & Info Endpoints ====================

@app.get("/")
async def root():
    return {
        "message": "Clawbot API - Google Workspace Integration",
        "version": "1.0.0",
        "docs": "/docs",
        "features": [
            "Gmail integration",
            "Google Calendar integration",
            "GSuite Admin API integration",
            "Token caching",
            "Multi-agent routing",
            "Daily context memory",
            "Long-term memory",
            "Conversation history"
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "ok": True,
        "timestamp": datetime.utcnow().isoformat(),
        "token_cache_type": settings.TOKEN_CACHE_TYPE,
        "multi_agent_enabled": settings.ENABLE_MULTI_AGENT,
        "routing_strategy": settings.AGENT_ROUTING_STRATEGY
    }
