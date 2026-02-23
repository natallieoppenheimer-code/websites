"""
Look up a person's phone and email via the USA People Search RapidAPI.

Given a first name, last name, and state (from BizFile), we fetch the
first page of results and pick the best-matching record by prioritising:
  1. Records that have both a phone and an email
  2. Records whose city matches the registered agent city from BizFile
  3. WIRELESS phone numbers over LANDLINE
"""
import os
import logging
from dataclasses import dataclass, field
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_PEOPLE_KEY", "")
PEOPLE_API_HOST = "usa-people-search-public-records.p.rapidapi.com"
PEOPLE_API_URL = "https://usa-people-search-public-records.p.rapidapi.com/SearchPeople"


@dataclass
class ContactResult:
    full_name: str = ""
    best_phone: str = ""
    best_email: str = ""
    city: str = ""
    state: str = ""
    found: bool = False


async def find_contact(
    first_name: str,
    last_name: str,
    state: str = "CA",
    preferred_city: str = "",
) -> ContactResult:
    """
    Search for the owner by name + state and return the best contact match.
    preferred_city is used as a tie-breaker when multiple records exist.
    """
    if not first_name or not last_name:
        return ContactResult()

    headers = {
        "x-rapidapi-host": PEOPLE_API_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }
    params = {
        "FirstName": first_name,
        "LastName": last_name,
        "State": state,
        "Page": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(PEOPLE_API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning(f"People search failed for {first_name} {last_name}: {exc}")
        return ContactResult()

    records = data.get("Source1", [])
    if not records:
        logger.info(f"No people records found for {first_name} {last_name} in {state}.")
        return ContactResult()

    best = _pick_best(records, preferred_city)
    return best


def _pick_best(records: list[dict], preferred_city: str) -> ContactResult:
    """Score each record and return the best one."""

    def score(rec: dict) -> int:
        s = 0
        phones = rec.get("PeoplePhone") or []
        emails = rec.get("Email") or []
        has_phone = len(phones) > 0
        has_email = len(emails) > 0
        has_wireless = any(
            (p.get("LineType") or "").upper() == "WIRELESS" for p in phones
        )
        city = (rec.get("City") or "").upper()
        pref = preferred_city.upper()

        if has_phone and has_email:
            s += 10
        elif has_phone:
            s += 5
        elif has_email:
            s += 3
        if has_wireless:
            s += 4
        if pref and city == pref:
            s += 8
        elif pref and pref in city:
            s += 4
        return s

    ranked = sorted(records, key=score, reverse=True)
    top = ranked[0]

    phones = top.get("PeoplePhone") or []
    emails = top.get("Email") or []

    # Prefer WIRELESS; fall back to first available
    best_phone = ""
    for p in phones:
        if (p.get("LineType") or "").upper() == "WIRELESS":
            best_phone = p.get("PhoneNumber", "")
            break
    if not best_phone and phones:
        best_phone = phones[0].get("PhoneNumber", "")

    best_email = emails[0].get("Email", "") if emails else ""

    found = bool(best_phone or best_email)
    return ContactResult(
        full_name=top.get("FullName", ""),
        best_phone=_format_phone(best_phone),
        best_email=best_email.lower(),
        city=(top.get("City") or "").title(),
        state=top.get("State") or "CA",
        found=found,
    )


def _format_phone(raw: str) -> str:
    """Convert '4087017037' → '(408) 701-7037'."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if len(digits) == 11 and digits[0] == "1":
        d = digits[1:]
        return f"({d[:3]}) {d[3:6]}-{d[6:]}"
    return raw


def split_name(full_name: str) -> tuple[str, str]:
    """Split 'CHRIS JOHNSON' into ('CHRIS', 'JOHNSON')."""
    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]
