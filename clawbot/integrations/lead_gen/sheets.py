"""Google Sheets store for the lead generation pipeline.

Design principle: minimise API calls and respect quotas.
- Tab existence + header are set up ONCE via ensure_sheet().
- Deduplication uses an in-memory snapshot loaded ONCE per pipeline run.
- update_lead() batches all cell updates into a single batchUpdate call.
- All write/read calls are wrapped with exponential-backoff retry on 429.

Campaigns can use a separate tab via use_sheet_tab("Tab Name"); default tab is "Leads".
"""
import os
import time
import logging
import contextvars
from typing import Optional
from contextlib import contextmanager
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from clawbot.auth.oauth import get_google_credentials

logger = logging.getLogger(__name__)

SHEET_ID = os.getenv("LEAD_GEN_SHEET_ID", "")
# Email identity for outreach (natalie@equestrolabs.com = DreamHost; no Google needed for send).
GMAIL_USER = os.getenv("LEAD_GEN_GMAIL_USER", "natalie@equestrolabs.com")
# Google account that owns the Sheet (optional; defaults to GMAIL_USER). Use a Google-authorized user.
SHEET_USER = os.getenv("LEAD_GEN_SHEET_USER", GMAIL_USER)
TAB_NAME = "Leads"

# Optional tab override for campaigns (e.g. "Leads - Electrician South Bay")
_current_tab: contextvars.ContextVar[str] = contextvars.ContextVar("lead_gen_tab", default=TAB_NAME)


def get_tab_name() -> str:
    """Return the current sheet tab name (default "Leads", or override set by use_sheet_tab)."""
    return _current_tab.get()


@contextmanager
def use_sheet_tab(tab_name: str):
    """Temporarily use a different sheet tab for all sheet operations (e.g. campaign-specific tab)."""
    token = _current_tab.set(tab_name)
    try:
        yield
    finally:
        _current_tab.reset(token)

HEADERS = [
    "ID",
    "Business Name",
    "Category",
    "Area",
    "Biz Phone",
    "Website",
    "Biz Address",
    "Owner Name",
    "Owner City",
    "Owner State",
    "Best Phone",
    "Best Email",
    "Status",
    "SMS Sent",
    "Email Sent",
    "Date Added",
    "Notes",
    "Drip Step",       # 0=new, 1=touch1 sent, 2=touch2 sent, 3=touch3 sent
    "Next Contact",    # YYYY-MM-DD when next follow-up should fire
]

COL = {h: i for i, h in enumerate(HEADERS)}


# ── Retry helper ──────────────────────────────────────────────────────────────

def _with_retry(fn, max_attempts: int = 6, base_delay: float = 5.0):
    """Call fn(); on HTTP 429 back off and retry up to max_attempts times."""
    for attempt in range(max_attempts):
        try:
            return fn()
        except HttpError as exc:
            if exc.resp.status == 429 and attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Sheets quota 429 — waiting {delay:.0f}s (attempt {attempt+1}/{max_attempts})")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Exceeded retry attempts for Sheets API call")


# ── Service helper ────────────────────────────────────────────────────────────

def _service():
    creds = get_google_credentials(SHEET_USER)
    if not creds:
        raise RuntimeError(
            f"No Google credentials for Sheets user {SHEET_USER}. "
            f"Visit /auth/authorize?user_id={SHEET_USER} to authorize (use a Google account that has the sheet)."
        )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


# ── One-time sheet setup (called once per pipeline run) ───────────────────────

def ensure_sheet() -> None:
    """
    Ensure the current tab exists and has a header row.
    Makes at most 2 API calls (1 read metadata + 1 write if needed).
    Call this ONCE at the start of a pipeline run.
    """
    svc = _service()
    tab = get_tab_name()

    # Get spreadsheet metadata to check tab titles
    meta = _with_retry(lambda: svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute())
    sheets_list = meta.get("sheets", [])
    titles = [s["properties"]["title"] for s in sheets_list]

    if tab not in titles:
        if tab == TAB_NAME and sheets_list and titles[0] not in (TAB_NAME,):
            first_sheet_id = sheets_list[0]["properties"]["sheetId"]
            _with_retry(lambda: svc.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={"requests": [{"updateSheetProperties": {
                    "properties": {"sheetId": first_sheet_id, "title": TAB_NAME},
                    "fields": "title",
                }}]},
            ).execute())
            logger.info(f"Renamed '{titles[0]}' → '{TAB_NAME}'.")
        else:
            _with_retry(lambda: svc.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
            ).execute())
            logger.info(f"Created tab '{tab}'.")

    result = _with_retry(lambda: svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{tab}!1:1"
    ).execute())
    existing_headers = result.get("values", [[]])[0] if result.get("values") else []

    if not existing_headers:
        # Brand new sheet — write full header
        _with_retry(lambda: svc.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{tab}!A1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute())
        logger.info("Header row written.")
    else:
        # Append any missing columns to the right of the existing header
        missing = [h for h in HEADERS if h not in existing_headers]
        if missing:
            next_col = _col_letter(len(existing_headers))
            _with_retry(lambda: svc.spreadsheets().values().update(
                spreadsheetId=SHEET_ID,
                range=f"{tab}!{next_col}1",
                valueInputOption="RAW",
                body={"values": [missing]},
            ).execute())
            logger.info(f"Added missing header columns: {missing}")


# ── Bulk read (one API call, cache in memory) ─────────────────────────────────

def get_all_leads() -> list[dict]:
    """Read all rows from the sheet. One API call total."""
    svc = _service()
    tab = get_tab_name()
    try:
        result = _with_retry(lambda: svc.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=f"{tab}!A1:Z"
        ).execute())
    except Exception as exc:
        if "Unable to parse range" in str(exc):
            return []
        raise
    rows = result.get("values", [])
    if len(rows) < 2:
        return []
    header = rows[0]
    out = []
    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        out.append(dict(zip(header, padded)))
    return out


def load_existing_names(area: str) -> set[str]:
    """
    Return a set of lowercased business names already in the sheet for this area.
    One API call — used by sourcer.py to deduplicate before appending.
    """
    svc = _service()
    tab = get_tab_name()
    try:
        result = _with_retry(lambda: svc.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=f"{tab}!B:D"
        ).execute())
    except Exception as exc:
        if "Unable to parse range" in str(exc):
            return set()
        raise
    rows = result.get("values", [])
    existing = set()
    for i, row in enumerate(rows):
        if i == 0:
            continue  # skip header
        name = row[0].strip().lower() if len(row) > 0 else ""
        row_area = row[2].strip().lower() if len(row) > 2 else ""
        if name and row_area == area.strip().lower():
            existing.add(name)
    return existing


def load_sms_sent_phones(tabs: Optional[list] = None) -> set:
    """
    Return a set of E.164-normalised phones that have already received Touch-1
    SMS across ALL lead-gen tabs (or the given list of tabs).

    Used by the outreach layer to prevent duplicate messages to the same number
    even when the same business appears in multiple campaign tabs.
    """
    import re
    default_tabs = [
        "Leads",
        "Leads - Plumber Feb26",
        "Leads - Electrician Feb26",
        "Leads - HVAC Feb26",
        "Leads - Electrician South Bay",
        "Leads - Pool Cleaner South Bay",
    ]
    check_tabs = tabs or default_tabs
    svc = _service()
    sent = set()

    def _normalise(phone: str) -> str:
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            digits = "1" + digits
        return "+" + digits if digits else ""

    for tab in check_tabs:
        try:
            result = _with_retry(lambda t=tab: svc.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range=f"{t}!A1:Z",
            ).execute())
            rows = result.get("values", [])
            if len(rows) < 2:
                continue
            header = rows[0]
            try:
                sms_col   = header.index("SMS Sent")
                phone_col = header.index("Best Phone")
                biz_col   = header.index("Biz Phone")
            except ValueError:
                continue
            for row in rows[1:]:
                sms_sent = (row[sms_col].strip().upper() if len(row) > sms_col else "")
                if sms_sent != "YES":
                    continue
                phone = (row[phone_col].strip() if len(row) > phone_col else "") or \
                        (row[biz_col].strip()   if len(row) > biz_col   else "")
                normalised = _normalise(phone)
                if normalised:
                    sent.add(normalised)
        except Exception as exc:
            logger.debug("load_sms_sent_phones: tab '%s' error: %s", tab, exc)

    logger.info("[dedup] %d unique phones already received Touch-1 across all tabs", len(sent))
    return sent


def find_lead_row(business_name: str, area: str) -> Optional[int]:
    """
    Return 1-based row index of a matching lead, or None.
    Only used for the synchronous update path; sourcer uses load_existing_names instead.
    One API call.
    """
    svc = _service()
    tab = get_tab_name()
    try:
        result = _with_retry(lambda: svc.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=f"{tab}!B:D"
        ).execute())
    except Exception as exc:
        if "Unable to parse range" in str(exc):
            return None
        raise
    rows = result.get("values", [])
    for i, row in enumerate(rows):
        if i == 0:
            continue
        name_col = row[0].strip().lower() if len(row) > 0 else ""
        area_col = row[2].strip().lower() if len(row) > 2 else ""
        if name_col == business_name.strip().lower() and area_col == area.strip().lower():
            return i + 1  # 1-based (row 1 = header, row 2 = first data row)
    return None


# ── Write helpers ─────────────────────────────────────────────────────────────

def append_lead(row: dict) -> int:
    """
    Append one lead row. Returns the 1-based sheet row index.
    One API call.
    """
    svc = _service()
    tab = get_tab_name()
    values = [row.get(h, "") for h in HEADERS]
    result = _with_retry(lambda: svc.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{tab}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    ).execute())
    updated_range = result.get("updates", {}).get("updatedRange", "")
    try:
        row_index = int(updated_range.split("!")[-1].split(":")[0][1:])
    except Exception:
        row_index = -1
    logger.info(f"Appended '{row.get('Business Name')}' at row {row_index}.")
    return row_index


def update_lead(row_index: int, updates: dict) -> None:
    """
    Update multiple cells for a single lead row in ONE batchUpdate call.
    """
    if not updates or row_index <= 0:
        return
    svc = _service()
    tab = get_tab_name()
    data = []
    for col_name, value in updates.items():
        if col_name not in COL:
            continue
        col_letter = _col_letter(COL[col_name])
        data.append({
            "range": f"{tab}!{col_letter}{row_index}",
            "values": [[value]],
        })
    if not data:
        return
    _with_retry(lambda: svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "RAW", "data": data},
    ).execute())
    logger.info(f"Updated row {row_index}: {list(updates.keys())}")


# ── Utility ───────────────────────────────────────────────────────────────────

def _col_letter(zero_index: int) -> str:
    """Convert a zero-based column index to a Sheets column letter."""
    result = ""
    n = zero_index
    while True:
        result = chr(65 + n % 26) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result
