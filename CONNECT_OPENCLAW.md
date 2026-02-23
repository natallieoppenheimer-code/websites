# Connect OpenClaw to Clawbot

You run **OpenClaw TUI** and connect it to the OpenClaw gateway. This guide shows how to connect that stack to **Clawbot** so the assistant can use Gmail, Calendar, Memory, and SMS.

## The Two Sides

| Service | What it is | URL |
|--------|-------------|-----|
| **OpenClaw** | TUI + gateway (your assistant) | TUI → `ws://127.0.0.1:18789` |
| **Clawbot** | API for Gmail, Calendar, Memory, SMS | `http://localhost:8000` |

**Connection** = OpenClaw (gateway/agent) is configured to **call** Clawbot’s HTTP API.

## 1. Start both (two terminals)

**Terminal 1 – Clawbot (already running):**
```bash
cd /Users/paulocfborges/Desktop/dev
./start_clawbot.sh
```
Leave it running. Clawbot is now at **http://localhost:8000**.

**Terminal 2 – OpenClaw gateway + TUI:**
```bash
# Start OpenClaw gateway first (if it’s not a single command)
# Then:
openclaw tui \
  --url ws://127.0.0.1:18789 \
  --password CrazyClaw1!
```

So you have:
- OpenClaw TUI talking to the gateway at `ws://127.0.0.1:18789`
- Clawbot API at `http://localhost:8000`

## 2. Point OpenClaw at Clawbot

OpenClaw must be told to use Clawbot as an **external API/tool**. That’s usually done in one of these ways:

### A. OpenClaw config file

If OpenClaw uses a config file (e.g. `~/.openclaw/config.yaml`, `~/.config/openclaw/config.yaml`, or a path shown in `openclaw --help`):

- Add a **custom API** or **tools** section.
- Set the **base URL** to: `http://localhost:8000`
- Add the Clawbot endpoints you need (see table below).

### B. OpenClaw UI / dashboard

If OpenClaw has a web UI or dashboard for “Tools” / “Integrations” / “Custom APIs”:

- Add a new API.
- **Base URL:** `http://localhost:8000`
- Use the paths from the table below (e.g. `/gmail/messages`, `/memory/store`).

### C. Environment variable (if supported)

Some setups allow something like:

```bash
export OPENCLAW_CLAWBOT_URL=http://localhost:8000
# or
export OPENCLAW_TOOLS_URL=http://localhost:8000
```

Then start OpenClaw. Check OpenClaw docs or `openclaw --help` for the exact variable names.

## 3. Clawbot endpoints to expose to OpenClaw

Use **base URL:** `http://localhost:8000`

| What | Method | Path | Main params |
|------|--------|------|-------------|
| Health | GET | `/health` | — |
| Gmail list | GET | `/gmail/messages` | `user_id`, `query`, `max_results` |
| Gmail send | POST | `/gmail/send` | `user_id`, `to`, `subject`, `body` |
| Calendar list | GET | `/calendar/events` | `user_id`, `max_results` |
| Calendar create | POST | `/calendar/events` | `user_id`, `summary`, `start_time`, `end_time`, optional: `add_meet_link` (true = video call) |
| Store memory | POST | `/memory/store` | `user_id`, `content`, `importance` |
| Daily context | GET | `/memory/daily` | `user_id`, `include_summary` |
| Long-term summary | GET | `/memory/long-term/summary` | `user_id`, `days` |
| Send SMS (TextLink) | POST | `/send-sms` | JSON body: `phone_number`, `text` |

Full list and request/response shapes: open **http://localhost:8000/docs** in a browser while Clawbot is running.

## 4. Calendar access (events and video calls)

To let OpenClaw read and write your calendar (create events, schedule calls):

1. **Run Clawbot** – `./start_clawbot.sh` so the API is at `http://localhost:8000`.
2. **Authorize Google Calendar once** – In a browser open:
   ```
   http://localhost:8000/auth/authorize?user_id=YOUR_USER_ID
   ```
   Sign in with Google and allow access to Calendar (and Gmail if you use it). Use the same `user_id` in OpenClaw.
3. **Expose calendar endpoints in OpenClaw** – In OpenClaw’s config or “Custom API / Tools” add:
   - **List events:** GET `http://localhost:8000/calendar/events` with `user_id`, optional `max_results`, `time_min`, `time_max`.
   - **Create event:** POST `http://localhost:8000/calendar/events` with `user_id`, `summary`, `start_time`, `end_time`; optional: `description`, `location`, `attendees`, `add_meet_link=true` (for a Google Meet video call link).
   - **Get event:** GET `http://localhost:8000/calendar/events/{event_id}` with `user_id`.
   - **Delete event:** DELETE `http://localhost:8000/calendar/events/{event_id}` with `user_id`.

After that, OpenClaw can list your events and create new ones (including events with a Meet link when you use `add_meet_link=true`).

## 5. User ID and auth

- **`user_id`**  
  Use one consistent id for the human using OpenClaw (e.g. your email or a short handle like `paul`). Pass it in every Clawbot call that needs `user_id`.

- **Natalie email (DreamHost)**  
  For **natalie@equestrolabs.com** you don’t need Google OAuth. Set `NATALIE_EMAIL` and `NATALIE_EMAIL_PASSWORD` in `.env`; use `user_id=natalie@equestrolabs.com` for `/gmail/messages` and `/gmail/send`. OpenClaw and lead-gen use this address by default.

- **Google (Gmail/Calendar)**  
  For other `user_id`s, complete OAuth once:
  1. In a browser open:  
     `http://localhost:8000/auth/authorize?user_id=YOUR_USER_ID`
  2. Sign in with Google and allow access.
  3. After that, Clawbot will use stored tokens for that `user_id`.

## 6. Quick test from your Mac

With Clawbot running:

```bash
# Health
curl http://localhost:8000/health

# Memory (no auth)
curl -X POST "http://localhost:8000/memory/store?user_id=paul&content=Test&importance=0.7"
curl "http://localhost:8000/memory/daily?user_id=paul&include_summary=true"
```

If these return JSON, OpenClaw can use the same URLs once it’s configured to call `http://localhost:8000`.

## Summary

- **OpenClaw TUI** → `ws://127.0.0.1:18789` (your existing command).
- **Clawbot** → `http://localhost:8000` (start with `./start_clawbot.sh`).
- **Connect them** by adding Clawbot as a custom API in OpenClaw’s config or UI with base URL `http://localhost:8000` and the paths above.

If you tell me where OpenClaw stores its config (file path or “only in UI”), I can adapt this into exact steps for your setup.
