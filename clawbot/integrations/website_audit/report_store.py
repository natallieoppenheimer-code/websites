"""
Persist and retrieve audit report data so shareable report pages can be rendered.

Reports are stored as JSON files in:
  clawbot/integrations/website_audit/reports/{slug}.json

The JSON schema mirrors report_to_dict() plus business metadata.
"""
import json
import pathlib
from typing import Optional

REPORTS_DIR = pathlib.Path(__file__).parent / "reports"


def save_report(
    slug: str,
    business_name: str,
    audited_url: str,
    report_dict: dict,
    demo_url: str = "",
) -> pathlib.Path:
    """Write report JSON to disk. Returns the path written."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "slug": slug,
        "business_name": business_name,
        "audited_url": audited_url,
        "demo_url": demo_url,
        **report_dict,
    }
    path = REPORTS_DIR / f"{slug}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_report(slug: str) -> Optional[dict]:
    """Load report JSON by slug, or None if not found."""
    path = REPORTS_DIR / f"{slug}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
