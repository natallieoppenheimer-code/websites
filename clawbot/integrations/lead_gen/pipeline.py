"""
Orchestrates the full lead generation pipeline:
  1. Source leads from RapidAPI
  2. Enrich each new lead: BizFile lookup → People Search → Touch 1 SMS
  3. Drip follow-ups: Touch 2 SMS (Day 3), Touch 3 email (Day 7)
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional

from clawbot.integrations.lead_gen import sheets as sh
from clawbot.integrations.lead_gen.sourcer import source_leads
from clawbot.integrations.lead_gen.bizfile import lookup_owner
from clawbot.integrations.lead_gen.enricher import find_contact, split_name
from clawbot.integrations.lead_gen.outreach import (
    send_touch1, send_touch2, send_touch3,
)

logger = logging.getLogger(__name__)

# Statuses that are eligible for each drip touch
_TOUCH1_STATUSES = {"sourced", "enriched", "no_bizfile"}
_TOUCH2_STATUSES = {"touch1_sent"}
_TOUCH3_STATUSES = {"touch2_sent"}
_TERMINAL_STATUSES = {"drip_complete", "no_contact", "unsubscribed"}


# ── Enrich + Touch 1 ─────────────────────────────────────────────────────────

async def _enrich_and_touch1(lead: dict) -> dict:
    """
    For a single sourced lead: BizFile → People Search → Touch 1 SMS.
    Returns a summary dict.
    """
    business_name = lead.get("Business Name", "")
    row_index     = lead.get("_row_index", -1)
    logger.info(f"[Pipeline] Enriching: '{business_name}'")

    enriched_lead = dict(lead)
    sheet_updates: dict = {}

    # ── BizFile lookup ────────────────────────────────────────────────────────
    biz_result = await lookup_owner(business_name)

    if biz_result.found:
        owner_name  = biz_result.owner_name
        owner_city  = biz_result.owner_city
        owner_state = biz_result.owner_state
        logger.info(f"  BizFile → {owner_name} ({owner_city}, {owner_state})")
        sheet_updates.update({
            "Owner Name":  owner_name,
            "Owner City":  owner_city,
            "Owner State": owner_state,
        })

        # People Search for personal phone/email
        first, last = split_name(owner_name)
        contact = await find_contact(
            first_name=first,
            last_name=last,
            state=owner_state,
            preferred_city=owner_city,
        )
        if contact.found:
            sheet_updates["Best Phone"] = contact.best_phone
            sheet_updates["Best Email"] = contact.best_email
            enriched_lead["Best Phone"]  = contact.best_phone
            enriched_lead["Best Email"]  = contact.best_email
            logger.info(f"  People → phone: {contact.best_phone}, email: {contact.best_email}")
        else:
            logger.info(f"  People → no contact found for {owner_name}")

        sheet_updates["Status"] = "enriched"

    else:
        # Fall back to business phone from lead-gen API
        biz_phone = lead.get("Biz Phone", "")
        logger.info(f"  BizFile → not found, using biz phone: {biz_phone or 'none'}")
        sheet_updates["Owner Name"] = "not found"
        sheet_updates["Status"]     = "no_bizfile"
        if biz_phone:
            enriched_lead["Best Phone"] = biz_phone
            sheet_updates["Best Phone"] = biz_phone

    if row_index > 0:
        sh.update_lead(row_index, sheet_updates)
    enriched_lead.update(sheet_updates)

    # ── Touch 1: Intro SMS ────────────────────────────────────────────────────
    # Guard: never send Touch 1 twice (prevents duplicates if sheet was stale)
    if (enriched_lead.get("SMS Sent") or "").strip().upper() == "YES":
        logger.info(f"  Skipping Touch 1 for '{business_name}' — already sent.")
        return {"business": business_name, "owner": biz_result.owner_name or None, "sms": False, "email": False}

    has_contact = bool(enriched_lead.get("Best Phone") or enriched_lead.get("Best Email"))
    if has_contact:
        result = await send_touch1(enriched_lead, row_index)
    else:
        logger.info(f"  No contact for '{business_name}', skipping Touch 1.")
        result = {"sms": False, "email": False}
        if row_index > 0:
            sh.update_lead(row_index, {"Status": "no_contact"})

    return {
        "business": business_name,
        "owner":    biz_result.owner_name or None,
        "sms":      result["sms"],
        "email":    result["email"],
    }


# ── Drip follow-ups ───────────────────────────────────────────────────────────

async def _run_drip_followups(area: str, category: str) -> tuple[int, int]:
    """
    Check all leads for pending Touch 2 / Touch 3 and fire them if due today.
    Returns (touch2_sent, touch3_sent) counts.
    """
    all_rows = sh.get_all_leads()
    today    = date.today().isoformat()
    t2_sent  = 0
    t3_sent  = 0

    for i, row in enumerate(all_rows):
        # Filter by area + category
        if (
            row.get("Area", "").strip().lower() != area.strip().lower()
            or row.get("Category", "").strip().lower() != category.strip().lower()
        ):
            continue

        status       = row.get("Status", "").lower()
        next_contact = (row.get("Next Contact") or "").strip()
        drip_step    = row.get("Drip Step", "0").strip()
        row_index    = i + 2  # 1-based + header

        if status in _TERMINAL_STATUSES:
            continue

        # Only fire if today >= Next Contact date (or no date set — fire anyway)
        if next_contact and next_contact > today:
            continue

        row["_row_index"] = row_index

        # Touch 2: competitor message (local company saw big results)
        if status in _TOUCH2_STATUSES or drip_step == "1":
            logger.info(f"[Drip] Touch 2 (competitor) → '{row.get('Business Name')}'")
            r = await send_touch2(row, row_index)
            if r["sms"]:
                t2_sent += 1

        # Touch 3: email with phone — only if Drip Step is 2 (Touch 2 already sent)
        elif status in _TOUCH3_STATUSES or drip_step == "2":
            logger.info(f"[Drip] Touch 3 → '{row.get('Business Name')}'")
            r = await send_touch3(row, row_index)
            if r["email"]:
                t3_sent += 1

    return t2_sent, t3_sent


# ── Main pipeline entry point ─────────────────────────────────────────────────

async def run_pipeline(
    area: str,
    category: str,
    max_concurrent: int = 1,
    sheet_tab: Optional[str] = None,
    max_to_process: Optional[int] = None,
) -> dict:
    """
    Full pipeline entry point.

    1. Ensure the sheet tab exists (default "Leads", or sheet_tab if provided).
    2. Source new leads and enrich them (BizFile + People Search + Touch 1).
    3. Run drip follow-ups for leads due today (Touch 2 and Touch 3).

    If max_to_process is set (e.g. 1 for E2E test), only that many leads are
    enriched and sent Touch 1; drip follow-ups still run for all due leads.
    """
    started_at = datetime.now().isoformat()
    logger.info(
        f"[Pipeline] START — area='{area}', category='{category}'"
        + (f" (tab={sheet_tab})" if sheet_tab else "")
        + (f" max_to_process={max_to_process}" if max_to_process is not None else "")
    )

    if sheet_tab:
        with sh.use_sheet_tab(sheet_tab):
            return await _run_pipeline_impl(area, category, max_concurrent, started_at, max_to_process)
    return await _run_pipeline_impl(area, category, max_concurrent, started_at, max_to_process)


async def _run_pipeline_impl(
    area: str,
    category: str,
    max_concurrent: int,
    started_at: str,
    max_to_process: Optional[int] = None,
) -> dict:
    """Pipeline implementation (runs inside optional use_sheet_tab)."""
    sh.ensure_sheet()

    # ── Source + Touch 1 ──────────────────────────────────────────────────────
    new_leads = await source_leads(area, category)
    logger.info(f"[Pipeline] {len(new_leads)} new leads sourced.")

    # Pick up previously sourced leads that didn't get a Touch 1 yet
    # IMPORTANT: Exclude any lead that already got Touch 1 (SMS Sent=YES or Drip Step>=1)
    # to prevent duplicate intro messages.
    all_rows = sh.get_all_leads()
    pending  = []
    for i, row in enumerate(all_rows):
        status   = row.get("Status", "").lower()
        sms_sent = (row.get("SMS Sent") or "").strip().upper()
        drip     = (row.get("Drip Step") or "0").strip()

        # Skip if already sent Touch 1
        if sms_sent == "YES" or drip in ("1", "2", "3"):
            continue
        if (
            status in _TOUCH1_STATUSES
            and row.get("Area", "").strip().lower()     == area.strip().lower()
            and row.get("Category", "").strip().lower() == category.strip().lower()
        ):
            row["_row_index"] = i + 2
            pending.append(row)

    new_names = {r.get("Business Name", "").strip().lower() for r in new_leads}
    pending   = [r for r in pending if r.get("Business Name", "").strip().lower() not in new_names]

    all_to_enrich = new_leads + pending
    if max_to_process is not None and max_to_process >= 0:
        all_to_enrich = all_to_enrich[:max_to_process]
        logger.info(
            f"[Pipeline] Limiting to {max_to_process} lead(s). "
            f"{len(new_leads)} new + {len(pending)} pending → {len(all_to_enrich)} to enrich."
        )
    else:
        logger.info(
            f"[Pipeline] {len(new_leads)} new + {len(pending)} pending = "
            f"{len(all_to_enrich)} to enrich for Touch 1."
        )

    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded(lead: dict) -> dict:
        async with semaphore:
            return await _enrich_and_touch1(lead)

    results = []
    if all_to_enrich:
        results = await asyncio.gather(*[bounded(lead) for lead in all_to_enrich])

    touch1_sent = sum(1 for r in results if r.get("sms") or r.get("email"))
    enriched    = sum(1 for r in results if r.get("owner"))

    # ── Drip follow-ups (Touch 2 + Touch 3) ──────────────────────────────────
    touch2_sent, touch3_sent = await _run_drip_followups(area, category)

    summary = {
        "area":         area,
        "category":     category,
        "started_at":   started_at,
        "finished_at":  datetime.now().isoformat(),
        "new_leads":    len(new_leads),
        "enriched":     enriched,
        "touch1_sent":  touch1_sent,
        "touch2_sent":  touch2_sent,
        "touch3_sent":  touch3_sent,
    }
    logger.info(f"[Pipeline] DONE — {summary}")
    return summary
