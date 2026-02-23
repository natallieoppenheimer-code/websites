"""
Persist and retrieve audit report data so shareable report pages can be rendered.

Primary storage: JSON file on disk at:
  clawbot/integrations/website_audit/reports/{slug}.json

Fallback (survives Render ephemeral-disk restarts):
  Google Sheets "Website Customers" tab → "Report JSON" column
"""
import json
import logging
import pathlib
from typing import Optional

logger = logging.getLogger(__name__)

REPORTS_DIR = pathlib.Path(__file__).parent / "reports"


def save_report(
    slug: str,
    business_name: str,
    audited_url: str,
    report_dict: dict,
    demo_url: str = "",
) -> pathlib.Path:
    """Write report JSON to disk AND to Google Sheets. Returns the disk path."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "slug": slug,
        "business_name": business_name,
        "audited_url": audited_url,
        "demo_url": demo_url,
        **report_dict,
    }
    path = REPORTS_DIR / f"{slug}.json"
    json_str = json.dumps(data, indent=2)
    path.write_text(json_str, encoding="utf-8")

    # Also save to Google Sheets so the report survives Render restarts
    try:
        from clawbot.integrations.website_customers.sheets import save_report_json
        save_report_json(slug, json_str)
    except Exception as exc:
        logger.warning("Could not save report JSON to Sheets (non-fatal): %s", exc)

    return path


def load_report(slug: str) -> Optional[dict]:
    """Load report JSON by slug.

    Checks disk first, then falls back to Google Sheets (so reports survive
    Render's ephemeral filesystem restarts). If found in Sheets but not on
    disk, writes the file back to disk for faster subsequent loads.
    """
    path = REPORTS_DIR / f"{slug}.json"

    # 1. Try disk
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 2. Fall back to Google Sheets
    logger.info("Report not on disk — trying Google Sheets for slug '%s'", slug)
    try:
        from clawbot.integrations.website_customers.sheets import load_report_json
        json_str = load_report_json(slug)
        if json_str:
            data = json.loads(json_str)
            # Write back to disk for subsequent fast loads
            try:
                REPORTS_DIR.mkdir(parents=True, exist_ok=True)
                path.write_text(json_str, encoding="utf-8")
                logger.info("Restored report to disk from Sheets for slug '%s'", slug)
            except Exception:
                pass
            return data
    except Exception as exc:
        logger.warning("Could not load report JSON from Sheets: %s", exc)

    return None
