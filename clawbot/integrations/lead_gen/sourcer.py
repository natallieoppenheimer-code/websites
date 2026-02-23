"""Fetch small-business leads from the RapidAPI lead-generation endpoint."""
import os
import uuid
import logging
from datetime import datetime
from typing import Optional
import httpx

from clawbot.integrations.lead_gen import sheets as sh

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_LEAD_KEY", "")
LEAD_API_HOST = "lead-generation2.p.rapidapi.com"
LEAD_API_URL = "https://lead-generation2.p.rapidapi.com/lead"


async def fetch_leads(area: str, category: str) -> list[dict]:
    """Call the lead-generation API and return the raw result list."""
    headers = {
        "x-rapidapi-host": LEAD_API_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }
    params = {"area": area, "search": category}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(LEAD_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    results = data.get("result", [])
    logger.info(f"Fetched {len(results)} leads for '{category}' in '{area}'.")
    return results


def _extract_phone(other_info: Optional[str]) -> str:
    """Pull the phone number out of the 'other-info' string, e.g. 'Open 24 hours · (408) 701-7037'."""
    if not other_info:
        return ""
    for part in other_info.split("·"):
        part = part.strip()
        if part.startswith("(") or (len(part) > 7 and part.replace("-", "").replace(" ", "").isdigit()):
            return part
    return ""


async def source_leads(area: str, category: str) -> list[dict]:
    """
    Fetch leads from API, deduplicate against existing sheet rows,
    and append new ones. Returns list of dicts for leads that were
    newly added (these still need BizFile + enrichment).

    Uses a single bulk read for deduplication (not one read per lead).
    """
    raw = await fetch_leads(area, category)
    newly_added = []
    today = datetime.now().strftime("%Y-%m-%d")

    # Load existing names ONCE — one API call for all deduplication
    existing_names = sh.load_existing_names(area)

    for item in raw:
        name = (item.get("name") or "").strip()
        if not name:
            continue

        # Deduplicate in memory
        if name.strip().lower() in existing_names:
            logger.debug(f"Skipping duplicate: '{name}' in '{area}'.")
            continue

        phone = _extract_phone(item.get("other-info"))
        address_raw = item.get("info") or ""
        # info is like "Plumber · 16825 Monterey Rd"
        address_parts = address_raw.split("·")
        address = address_parts[-1].strip() if len(address_parts) > 1 else ""

        row = {
            "ID": str(uuid.uuid4())[:8],
            "Business Name": name,
            "Category": category,
            "Area": area,
            "Biz Phone": phone,
            "Website": item.get("website") or "",
            "Biz Address": address,
            "Owner Name": "",
            "Owner City": "",
            "Owner State": "",
            "Best Phone": "",
            "Best Email": "",
            "Status": "sourced",
            "SMS Sent": "NO",
            "Email Sent": "NO",
            "Date Added": today,
            "Notes": "",
        }

        row_index = sh.append_lead(row)
        row["_row_index"] = row_index
        newly_added.append(row)
        logger.info(f"Added lead: '{name}' (row {row_index})")

    logger.info(f"Sourcing complete. {len(newly_added)} new leads added out of {len(raw)} fetched.")
    return newly_added
