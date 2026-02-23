"""
Persist and retrieve audit report data so shareable report pages can be rendered.

PRIMARY:  disk  – clawbot/integrations/website_audit/reports/{slug}.json
FALLBACK: Google Sheets – 'Report JSON' column of the Website Customers tab

This dual-layer approach survives Render's ephemeral filesystem: on redeploy
the JSON files vanish, but Sheets data persists and is used as the fallback.
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
    json_str = json.dumps(data, indent=2)

    # Write to disk (fast, ephemeral)
    path = REPORTS_DIR / f"{slug}.json"
    path.write_text(json_str, encoding="utf-8")
    logger.info("[report_store] Saved report to disk: %s", path)

    # Write to Sheets (persistent across Render redeploys)
    try:
        from clawbot.integrations.website_customers.sheets import save_report_json
        ok = save_report_json(slug, json_str)
        if ok:
            logger.info("[report_store] Saved report to Sheets for slug '%s'", slug)
        else:
            logger.warning("[report_store] Could not save to Sheets for slug '%s' (row may not exist yet)", slug)
    except Exception as exc:
        logger.warning("[report_store] Sheets write failed for '%s': %s", slug, exc)

    return path


def load_report(slug: str) -> Optional[dict]:
    """Load report JSON by slug.

    Checks disk first (fast), falls back to Google Sheets (persistent).
    """
    # 1. Try disk
    path = REPORTS_DIR / f"{slug}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data:
                return data
        except Exception:
            pass

    # 2. Fall back to Sheets
    try:
        from clawbot.integrations.website_customers.sheets import load_report_json
        json_str = load_report_json(slug)
        if json_str:
            data = json.loads(json_str)
            # Warm the disk cache so subsequent calls are faster
            try:
                REPORTS_DIR.mkdir(parents=True, exist_ok=True)
                path.write_text(json_str, encoding="utf-8")
            except Exception:
                pass
            logger.info("[report_store] Loaded report from Sheets for slug '%s'", slug)
            return data
    except Exception as exc:
        logger.warning("[report_store] Sheets read failed for '%s': %s", slug, exc)

    return None
