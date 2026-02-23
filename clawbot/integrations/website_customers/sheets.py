"""Google Sheets store for website customers (prospects + demo/live sites).

Uses the same spreadsheet as lead-gen (LEAD_GEN_SHEET_ID) with tab "Website Customers".
Columns: ID, Business Name, Contact Email, Contact Phone, Current Site URL,
Audit Score, Audit Date, Status, Alternative Site URL, Created At, Notes.
"""
import os
import time
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from clawbot.auth.oauth import get_google_credentials

logger = logging.getLogger(__name__)

SHEET_ID = os.getenv("LEAD_GEN_SHEET_ID", "")
SHEET_USER = os.getenv("LEAD_GEN_SHEET_USER", os.getenv("LEAD_GEN_GMAIL_USER", "natalie@equestrolabs.com"))
TAB_NAME = "Website Customers"

HEADERS = [
    "ID",
    "Business Name",
    "Contact Email",
    "Contact Phone",
    "Current Site URL",
    "Audit Score",
    "Audit Date",
    "Status",
    "Alternative Site URL",
    "Created At",
    "Notes",
    "Slug",
    "Business Phone",
    "Service Area",
    "Category",
    "Report JSON",   # Full audit report stored here for ephemeral-disk resilience
]

COL = {h: i for i, h in enumerate(HEADERS)}

STATUS_PROSPECT = "prospect"
STATUS_DEMO_BUILT = "demo_built"
STATUS_LIVE = "live"
STATUS_LOST = "lost"


def _with_retry(fn, max_attempts: int = 6, base_delay: float = 5.0):
    for attempt in range(max_attempts):
        try:
            return fn()
        except HttpError as exc:
            if exc.resp.status == 429 and attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning("Sheets quota 429 — waiting %ss (attempt %s/%s)", delay, attempt + 1, max_attempts)
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Exceeded retry attempts for Sheets API call")


def _service():
    creds = get_google_credentials(SHEET_USER)
    if not creds:
        raise RuntimeError(
            "No Google credentials for Website Customers sheet. "
            "Visit /auth/authorize?user_id=%s to authorize." % SHEET_USER
        )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _col_letter(zero_index: int) -> str:
    result = ""
    n = zero_index
    while True:
        result = chr(65 + n % 26) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result


def ensure_sheet() -> None:
    """Ensure the Website Customers tab exists and has header row."""
    if not SHEET_ID:
        raise RuntimeError("LEAD_GEN_SHEET_ID is not set; cannot create Website Customers tab.")
    svc = _service()
    meta = _with_retry(lambda: svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute())
    sheets_list = meta.get("sheets", [])
    titles = [s["properties"]["title"] for s in sheets_list]

    if TAB_NAME not in titles:
        _with_retry(lambda: svc.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": TAB_NAME}}}]},
        ).execute())
        logger.info("Created tab '%s'.", TAB_NAME)

    result = _with_retry(lambda: svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="%s!1:1" % TAB_NAME
    ).execute())
    existing_headers = result.get("values", [[]])[0] if result.get("values") else []

    if not existing_headers:
        _with_retry(lambda: svc.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range="%s!A1" % TAB_NAME,
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute())
        logger.info("Website Customers header row written.")


RENDER_BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://websites-natalie.onrender.com")


def register_customer(
    business_name: str,
    contact_email: str,
    current_site_url: str,
    contact_phone: Optional[str] = None,
    business_phone: Optional[str] = None,
    service_area: Optional[str] = None,
    category: Optional[str] = None,
    audit_score: Optional[float] = None,
    audit_findings_count: Optional[int] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Append a new website customer (prospect). Ensures sheet/tab exist.
    Auto-generates a demo site and writes the URL back into the sheet.
    Returns the created row as dict with ID and alternative_site_url.
    """
    from clawbot.integrations.website_audit.generator import generate_demo_html, slugify

    ensure_sheet()
    svc = _service()
    row_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    audit_date = now[:10] if (audit_score is not None or audit_findings_count is not None) else ""

    slug = slugify(business_name)
    alt_phone = business_phone or contact_phone or ""
    area = service_area or ""

    # Generate the demo HTML and persist to demos dir
    demo_html = generate_demo_html(
        business_name=business_name,
        business_phone=alt_phone,
        service_area=area,
        current_site_url=current_site_url,
        category=category or "",
        slug=slug,
        render_base_url=RENDER_BASE_URL,
    )
    _persist_demo(slug, demo_html)

    alternative_site_url = f"{RENDER_BASE_URL}/demos/{slug}"

    row = {
        "ID": row_id,
        "Business Name": (business_name or "").strip(),
        "Contact Email": (contact_email or "").strip(),
        "Contact Phone": (contact_phone or "").strip(),
        "Current Site URL": (current_site_url or "").strip(),
        "Audit Score": str(audit_score) if audit_score is not None else "",
        "Audit Date": audit_date,
        "Status": STATUS_DEMO_BUILT,
        "Alternative Site URL": alternative_site_url,
        "Created At": now,
        "Notes": (notes or "").strip(),
        "Slug": slug,
        "Business Phone": alt_phone,
        "Service Area": area,
        "Category": (category or "").strip(),
    }
    if audit_findings_count is not None:
        row["Notes"] = (row["Notes"] + ("; " if row["Notes"] else "") + "%s findings" % audit_findings_count).strip()

    values = [row.get(h, "") for h in HEADERS]
    _with_retry(lambda: svc.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="%s!A1" % TAB_NAME,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    ).execute())
    logger.info("Registered website customer: %s (%s) → %s", row["Business Name"], row_id, alternative_site_url)
    return row


def _persist_demo(slug: str, html: str) -> None:
    """Write generated HTML to the demos directory so it can be served."""
    import pathlib
    demos_dir = pathlib.Path(__file__).resolve().parents[2] / "website_audit" / "demos"
    demos_dir.mkdir(parents=True, exist_ok=True)
    (demos_dir / f"{slug}.html").write_text(html, encoding="utf-8")
    logger.info("Demo HTML written: demos/%s.html", slug)


def get_customer_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Return the customer row that matches the given slug, or None."""
    for customer in list_customers():
        if customer.get("Slug", "").strip() == slug.strip():
            return customer
    return None


def save_report_json(slug: str, report_json_str: str) -> bool:
    """Write a JSON string into the 'Report JSON' column for the matching slug row."""
    if not SHEET_ID:
        return False
    svc = _service()
    try:
        result = _with_retry(lambda: svc.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="%s!A1:Z" % TAB_NAME,
        ).execute())
    except Exception as exc:
        logger.warning("[save_report_json] Could not read sheet: %s", exc)
        return False

    rows = result.get("values", [])
    if len(rows) < 2:
        return False
    header = rows[0]
    if "Slug" not in header or "Report JSON" not in header:
        return False

    slug_col_idx = header.index("Slug")
    report_col_idx = header.index("Report JSON")

    for row_num, row in enumerate(rows[1:], start=2):
        padded = row + [""] * (max(slug_col_idx, report_col_idx) + 1 - len(row))
        if padded[slug_col_idx].strip() == slug.strip():
            col_letter = _col_letter(report_col_idx)
            try:
                _with_retry(lambda: svc.spreadsheets().values().update(
                    spreadsheetId=SHEET_ID,
                    range="%s!%s%s" % (TAB_NAME, col_letter, row_num),
                    valueInputOption="RAW",
                    body={"values": [[report_json_str]]},
                ).execute())
                logger.info("[save_report_json] Saved report JSON for slug '%s'", slug)
                return True
            except Exception as exc:
                logger.warning("[save_report_json] Write failed for '%s': %s", slug, exc)
                return False
    logger.warning("[save_report_json] No row found for slug '%s'", slug)
    return False


def load_report_json(slug: str) -> Optional[str]:
    """Return the stored JSON string from 'Report JSON' column for slug, or None."""
    customer = get_customer_by_slug(slug)
    if not customer:
        return None
    val = customer.get("Report JSON", "").strip()
    return val if val else None


def list_customers() -> List[Dict[str, Any]]:
    """Return all website customer rows."""
    if not SHEET_ID:
        return []
    svc = _service()
    try:
        result = _with_retry(lambda: svc.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="%s!A1:Z" % TAB_NAME,
        ).execute())
    except Exception as exc:
        if "Unable to parse range" in str(exc) or "404" in str(exc):
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


def _find_row_by_id(customer_id: str) -> Optional[int]:
    """Return 1-based row index for the given ID, or None."""
    if not SHEET_ID or not customer_id:
        return None
    svc = _service()
    try:
        result = _with_retry(lambda: svc.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="%s!A:A" % TAB_NAME,
        ).execute())
    except Exception as exc:
        if "Unable to parse range" in str(exc):
            return None
        raise
    rows = result.get("values", [])
    for i, row in enumerate(rows):
        if i == 0:
            continue
        if (row[0].strip() if row else "") == customer_id.strip():
            return i + 1
    return None


def update_customer(
    customer_id: str,
    status: Optional[str] = None,
    alternative_site_url: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    """
    Update a website customer by ID. Returns True if row was found and updated.
    """
    row_index = _find_row_by_id(customer_id)
    if not row_index:
        return False
    svc = _service()
    updates = {}
    if status is not None:
        updates["Status"] = status
    if alternative_site_url is not None:
        updates["Alternative Site URL"] = alternative_site_url
    if notes is not None:
        updates["Notes"] = notes
    if not updates:
        return True
    data = []
    for col_name, value in updates.items():
        if col_name not in COL:
            continue
        col_letter = _col_letter(COL[col_name])
        data.append({
            "range": "%s!%s%s" % (TAB_NAME, col_letter, row_index),
            "values": [[value]],
        })
    _with_retry(lambda: svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "RAW", "data": data},
    ).execute())
    logger.info("Updated website customer %s: %s", customer_id, list(updates.keys()))
    return True
