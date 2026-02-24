"""
3-touch drip outreach for Equestro Labs lead generation.

Touch 1 (Day 0)  — Intro SMS: who we are + what we do, ask if we can send more info.
Touch 2 (Day 3)  — Follow-up SMS: local competitor just used it + saw big results.
Touch 3 (Day 7)  — Email: full pitch, phone number included, ask if they want info over text.

All messages are sent via Clawbot:
  POST /send-sms  — TextLink SMS
  POST /gmail/send — Gmail (Touch 3 only)
"""
import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

from clawbot.integrations.lead_gen import sheets as sh

logger = logging.getLogger(__name__)

CLAWBOT_BASE = os.getenv("CLAWBOT_BASE_URL", "http://localhost:8000")
GMAIL_USER   = os.getenv("LEAD_GEN_GMAIL_USER", "natalie@equestrolabs.com")

# Natalie's phone (included in all messages so leads can text back)
NATALIE_PHONE = os.getenv("LEAD_GEN_NATALIE_PHONE", "+14087896543")

# Days between touches
TOUCH_2_DELAY = 3   # days after touch 1
TOUCH_3_DELAY = 7   # days after touch 1


# ── Phone formatting ──────────────────────────────────────────────────────────

def _e164(phone: str) -> str:
    """Normalize a US phone number to E.164 (+1XXXXXXXXXX)."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return phone


# ── Name helper ───────────────────────────────────────────────────────────────

_PLACEHOLDER_NAMES = {"not found", "not", "unknown", "n/a", "none", ""}

def _first_name(owner_name: str) -> str:
    """Return the owner's first name, or '' if unknown."""
    if not owner_name or not owner_name.strip():
        return ""
    first = owner_name.strip().split()[0].lower()
    if first in _PLACEHOLDER_NAMES:
        return ""
    return owner_name.strip().split()[0].title()


# ── Touch 1 — Intro SMS ───────────────────────────────────────────────────────

_T1_SMS: dict[str, str] = {
    "plumber": (
        "Hi {name}! I'm Natalie from Equestro Labs. We help plumbing companies "
        "eliminate double-bookings and auto-dispatch jobs with AI — no new software to learn. "
        "Can I send you a bit more info over text? 😊"
    ),
    "electrician": (
        "Hi {name}! I'm Natalie from Equestro Labs. We help electrical contractors "
        "automate scheduling and route techs smarter with AI. "
        "Mind if I shoot you a few details over text?"
    ),
    "hvac": (
        "Hi {name}! I'm Natalie from Equestro Labs. We help HVAC companies cut "
        "dispatch time and stop scheduling conflicts with AI. "
        "Can I send you a bit more info over text?"
    ),
    "landscaper": (
        "Hi {name}! I'm Natalie from Equestro Labs. We help landscaping businesses "
        "optimize crew routes and automate bookings with AI. "
        "Mind if I send over a few details?"
    ),
    "pest control": (
        "Hi {name}! I'm Natalie from Equestro Labs. We help pest control companies "
        "auto-schedule jobs and route techs efficiently with AI. "
        "Can I share a bit more over text?"
    ),
    "locksmith": (
        "Hi {name}! I'm Natalie from Equestro Labs. We help locksmiths dispatch "
        "faster and avoid double-bookings with AI. "
        "Mind if I send a few details over text?"
    ),
    "pool cleaner": (
        "Hi {name}! I'm Natalie from Equestro Labs. We help pool service companies "
        "eliminate route chaos and double-bookings — AI scheduling that adapts when "
        "techs call out or customers cancel, no more rebuilding routes from scratch. "
        "Mind if I send a few details over text?"
    ),
}


# ── Touch 2 — Competitor follow-up SMS ───────────────────────────────────────

_T2_SMS: dict[str, str] = {
    "plumber": (
        "Hey {name}, Natalie again from Equestro Labs! 👋 "
        "Just thought I'd mention — a local plumbing company in {area} recently "
        "set up our AI scheduling and saw a significant jump in booked jobs within "
        "the first few weeks. Happy to text you the details if you're curious!"
    ),
    "electrician": (
        "Hey {name}, Natalie from Equestro Labs here! "
        "Quick follow-up — an electrical contractor nearby just rolled out our "
        "AI dispatch and reported a big jump in completed jobs per day. "
        "Want me to text you more about how it works?"
    ),
    "hvac": (
        "Hey {name}, Natalie again! 👋 "
        "Heads up — a local HVAC company in your area just started using our AI "
        "scheduling and saw a major increase in leads booked. "
        "Happy to share more details over text if you're interested!"
    ),
    "landscaper": (
        "Hey {name}, Natalie from Equestro Labs! "
        "Just wanted to follow up — a landscaping company nearby just set up our "
        "route optimization AI and saw their crews finishing significantly more "
        "jobs per day. Want me to text you the details?"
    ),
    "pest control": (
        "Hey {name}, Natalie here again! "
        "A local pest control company just went live with our AI scheduling and "
        "saw a noticeable jump in bookings. "
        "Mind if I text you a quick overview of how it works?"
    ),
    "locksmith": (
        "Hey {name}, Natalie from Equestro Labs! "
        "Quick heads up — a locksmith in {area} just launched our AI dispatch "
        "and significantly cut their response time. "
        "Can I send you a bit more info over text?"
    ),
    "pool cleaner": (
        "Hey {name}, Natalie from Equestro Labs! "
        "Quick follow-up — a pool service company in {area} just rolled out our "
        "route optimization and cut wasted drive time by 20–30% and reschedules by a lot. "
        "Want me to text you more about how it works?"
    ),
}


# ── Touch 3 — Email ──────────────────────────────────────────────────────────

_T3_SUBJECTS: dict[str, str] = {
    "plumber":       "Following up — AI scheduling for {business}",
    "electrician":   "Following up — smarter dispatch for {business}",
    "hvac":          "Following up — eliminate scheduling conflicts at {business}",
    "landscaper":    "Following up — route optimization for {business}",
    "pest control":  "Following up — AI job scheduling for {business}",
    "locksmith":     "Following up — faster dispatch for {business}",
    "pool cleaner":  "Following up — no more route chaos for {business}",
}

_T3_EMAIL_BODY = """\
Hi {name},

I've reached out a couple of times over text — just wanted to follow up properly \
with a quick email.

I'm Natalie from Equestro Labs ({website}). We build lightweight AI tools for \
field-service businesses like {business}, specifically:

  • Smart scheduling that prevents double-bookings automatically
  • Route optimization that saves techs 20–40 min per day
  • Automatic dispatch — the right person goes to the right job, every time

A local {category} company in {area} recently set up our system and saw a \
significant jump in jobs booked within their first few weeks — and they were \
up and running in under a week with no new software to learn from scratch.

Would love to share a few more details if you're open to it. \
Feel free to reply to this email or just text me directly at {natalie_phone} — \
happy to keep things simple and answer any questions over text.

Best,
Natalie
Equestro Labs | {website}
Text/call: {natalie_phone}
"""


# ── Dry run (no real send; sheet still updated) ────────────────────────────────

def _is_dry_run() -> bool:
    v = os.getenv("LEAD_GEN_DRY_RUN", "").strip().lower()
    return v in ("1", "true", "yes")


# ── Low-level send helpers ────────────────────────────────────────────────────

async def _send_sms(phone: str, text: str) -> bool:
    formatted = _e164(phone)
    if _is_dry_run():
        logger.info(f"[DRY RUN] Would send SMS to {formatted}: {text[:60]}...")
        return True
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CLAWBOT_BASE}/send-sms",
                json={"phone_number": formatted, "text": text},
            )
            resp.raise_for_status()
            ok = resp.json().get("success", False)
            logger.info(f"SMS → {formatted}: {'OK' if ok else 'FAILED'}")
            return ok
    except Exception as exc:
        logger.warning(f"SMS failed → {formatted}: {exc}")
        return False


async def _send_email(to: str, subject: str, body: str) -> bool:
    if _is_dry_run():
        logger.info(f"[DRY RUN] Would send email to {to}: {subject[:50]}...")
        return True
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CLAWBOT_BASE}/gmail/send",
                params={
                    "user_id": GMAIL_USER,
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "body_type": "plain",
                },
            )
            resp.raise_for_status()
            logger.info(f"Email → {to}: OK")
            return True
    except Exception as exc:
        logger.warning(f"Email failed → {to}: {exc}")
        return False


# ── Public drip entry points ──────────────────────────────────────────────────

async def send_touch1(lead: dict, row_index: int) -> dict[str, bool]:
    """Send the initial intro SMS (Touch 1).

    Guards against sending the same message twice to the same phone number
    across all campaign sheet tabs (prevents duplicates when a business
    appears in multiple tabs or when the pipeline is re-run).
    """
    business = lead.get("Business Name", "your company")
    category = lead.get("Category", "plumber").lower().strip()
    name     = _first_name(lead.get("Owner Name", "")) or "there"
    phone    = lead.get("Best Phone", "") or lead.get("Biz Phone", "")

    sms_ok = False
    now    = datetime.now()

    if phone:
        # Cross-tab deduplication: refuse to SMS a number already contacted
        try:
            already_sent = sh.load_sms_sent_phones()
            e164 = _e164(phone)
            if e164 in already_sent:
                logger.info(
                    "[Touch 1] SKIPPED — %s already received Touch-1 on another tab (%s)",
                    e164, business,
                )
                return {"sms": False, "email": False}
        except Exception as exc:
            logger.warning("[Touch 1] Cross-tab dedup check failed (non-fatal): %s", exc)

        template = _T1_SMS.get(category, _T1_SMS["plumber"])
        text = template.format(name=name, business=business)
        sms_ok = await _send_sms(phone, text)

    next_contact = (now + timedelta(days=TOUCH_2_DELAY)).strftime("%Y-%m-%d")

    updates: dict = {
        "SMS Sent":     "YES" if sms_ok else ("FAILED" if phone else "NO PHONE"),
        "Drip Step":    "1" if sms_ok else "0",
        "Next Contact": next_contact if sms_ok else "",
        "Status":       "touch1_sent" if sms_ok else ("outreach_failed" if phone else "no_contact"),
        "Notes":        f"Touch 1 sent {now.strftime('%Y-%m-%d %H:%M')}" if sms_ok else f"Touch 1 failed {now.strftime('%Y-%m-%d %H:%M')}",
    }
    if row_index > 0:
        sh.update_lead(row_index, updates)

    return {"sms": sms_ok, "email": False}


async def send_touch2(lead: dict, row_index: int) -> dict[str, bool]:
    """Send the competitor follow-up SMS (Touch 2)."""
    business = lead.get("Business Name", "your company")
    category = lead.get("Category", "plumber").lower().strip()
    area     = (lead.get("Area", "") or "your area").replace(" CA", "").strip()
    name     = _first_name(lead.get("Owner Name", "")) or "there"
    phone    = lead.get("Best Phone", "")

    sms_ok = False
    now    = datetime.now()

    if phone:
        template = _T2_SMS.get(category, _T2_SMS["plumber"])
        text = template.format(name=name, business=business, area=area)
        sms_ok = await _send_sms(phone, text)

    next_contact = (now + timedelta(days=TOUCH_3_DELAY - TOUCH_2_DELAY)).strftime("%Y-%m-%d")

    updates: dict = {
        "Drip Step":    "2" if sms_ok else "1",
        "Next Contact": next_contact if sms_ok else "",
        "Status":       "touch2_sent" if sms_ok else "touch2_failed",
        "Notes":        f"Touch 2 sent {now.strftime('%Y-%m-%d %H:%M')}" if sms_ok else f"Touch 2 failed {now.strftime('%Y-%m-%d %H:%M')}",
    }
    if row_index > 0:
        sh.update_lead(row_index, updates)

    return {"sms": sms_ok, "email": False}


async def send_touch3(lead: dict, row_index: int) -> dict[str, bool]:
    """Send the follow-up email (Touch 3)."""
    business = lead.get("Business Name", "your company")
    category = lead.get("Category", "plumber").lower().strip()
    area     = (lead.get("Area", "") or "your area").replace(" CA", "").strip()
    name     = _first_name(lead.get("Owner Name", "")) or "there"
    email    = lead.get("Best Email", "")
    website  = "equestrolabs.com"

    email_ok = False
    now      = datetime.now()

    if email:
        subj_tmpl = _T3_SUBJECTS.get(category, _T3_SUBJECTS["plumber"])
        subject   = subj_tmpl.format(business=business)
        body      = _T3_EMAIL_BODY.format(
            name=name,
            business=business,
            category=category,
            area=area,
            website=website,
            natalie_phone=NATALIE_PHONE,
        )
        email_ok = await _send_email(email, subject, body)

    updates: dict = {
        "Email Sent":   "YES" if email_ok else ("FAILED" if email else "NO EMAIL"),
        "Drip Step":    "3" if email_ok else "2",
        "Next Contact": "",   # drip complete
        "Status":       "drip_complete" if email_ok else ("touch3_failed" if email else "no_email"),
        "Notes":        f"Touch 3 email sent {now.strftime('%Y-%m-%d %H:%M')}" if email_ok else f"Touch 3 skipped (no email) {now.strftime('%Y-%m-%d %H:%M')}",
    }
    if row_index > 0:
        sh.update_lead(row_index, updates)

    return {"sms": False, "email": email_ok}


# ── Backwards-compat alias used by older pipeline code ────────────────────────

async def send_outreach(lead: dict, row_index: int) -> dict[str, bool]:
    """Alias for Touch 1 — the initial outreach."""
    return await send_touch1(lead, row_index)
