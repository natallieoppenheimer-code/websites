#!/usr/bin/env python3
"""
End-to-end test for the lead generation pipeline with one lead.

Usage:
  # Dry run (no real SMS/email): inject one test lead, run pipeline for 1 lead
  python scripts/test_lead_pipeline_e2e.py --inject --dry-run

  # Live: inject one lead with your phone, run pipeline (sends real Touch 1 SMS)
  python scripts/test_lead_pipeline_e2e.py --inject --area "Morgan Hill CA" --category plumber \\
    --phone "+1XXXXXXXXXX"

  # No inject: run pipeline for area/category, process at most 1 lead (from RapidAPI or pending)
  python scripts/test_lead_pipeline_e2e.py --max-leads 1 --dry-run

Requires from .env: LEAD_GEN_SHEET_ID, RAPIDAPI_LEAD_KEY, RAPIDAPI_PEOPLE_KEY, CLAWBOT_BASE_URL.
For live send: TEXTLINK_API_KEY, and Google auth for Sheets (visit /auth/authorize?user_id=...).
Optional: BIZFILE_EMAIL, BIZFILE_PASSWORD for BizFile lookup.
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Load .env from repo root (optional)
_repo_root = Path(__file__).resolve().parent.parent
_env_file = _repo_root / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass

# Ensure repo root on path
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


def _check_env() -> List[str]:
    missing = []
    for key in ("LEAD_GEN_SHEET_ID", "RAPIDAPI_LEAD_KEY", "RAPIDAPI_PEOPLE_KEY", "CLAWBOT_BASE_URL"):
        if not os.getenv(key, "").strip():
            missing.append(key)
    return missing


def _inject_one_lead(area: str, category: str, business_name: str, biz_phone: str) -> int:
    from clawbot.integrations.lead_gen import sheets as sh

    sh.ensure_sheet()
    today = datetime.now().strftime("%Y-%m-%d")
    row = {
        "ID": "",
        "Business Name": business_name,
        "Category": category,
        "Area": area,
        "Biz Phone": biz_phone,
        "Website": "",
        "Biz Address": "",
        "Owner Name": "",
        "Owner City": "",
        "Owner State": "",
        "Best Phone": "",
        "Best Email": "",
        "Status": "sourced",
        "SMS Sent": "NO",
        "Email Sent": "NO",
        "Date Added": today,
        "Notes": "E2E test lead",
        "Drip Step": "0",
        "Next Contact": "",
    }
    row_index = sh.append_lead(row)
    print(f"[E2E] Injected 1 lead: '{business_name}' at row {row_index}")
    return row_index


async def _run(area: str, category: str, max_leads, dry_run: bool) -> dict:
    from clawbot.integrations.lead_gen.pipeline import run_pipeline

    if dry_run:
        os.environ["LEAD_GEN_DRY_RUN"] = "1"
        print("[E2E] DRY RUN: no real SMS or email will be sent; sheet will still be updated.")
    summary = await run_pipeline(
        area=area,
        category=category,
        max_concurrent=1,
        max_to_process=max_leads,
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run lead pipeline E2E test with one lead.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--area", default="Morgan Hill CA", help="Area for the lead(s)")
    parser.add_argument("--category", default="plumber", help="Category (plumber, electrician, etc.)")
    parser.add_argument("--inject", action="store_true", help="Inject one test lead into the sheet, then run pipeline")
    parser.add_argument("--business", default="E2E Test Lead", help="Business name (used when --inject)")
    parser.add_argument("--phone", default="", help="Biz phone for injected lead (required for real Touch 1)")
    parser.add_argument("--max-leads", type=int, default=None, help="Max leads to process (default: 1 when --inject)")
    parser.add_argument("--dry-run", action="store_true", help="Do not send real SMS/email (LEAD_GEN_DRY_RUN=1)")
    args = parser.parse_args()

    missing = _check_env()
    if missing:
        print("Missing required env:", ", ".join(missing))
        print("Set them in .env (see .env.example).")
        return 1

    if args.inject:
        phone = (args.phone or os.getenv("TEST_LEAD_PHONE", "")).strip()
        if not args.dry_run and not phone:
            print("For live run with --inject, set --phone or TEST_LEAD_PHONE so Touch 1 can be sent.")
            return 1
        _inject_one_lead(args.area, args.category, args.business, phone or "5550000000")
        max_leads = args.max_leads if args.max_leads is not None else 1
    else:
        max_leads = args.max_leads

    print(f"[E2E] Running pipeline: area={args.area!r}, category={args.category!r}, max_to_process={max_leads}")
    summary = asyncio.run(_run(args.area, args.category, max_leads, args.dry_run))

    print("\n[E2E] Pipeline summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("\n[E2E] Done. Check the Leads sheet for the updated row(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
