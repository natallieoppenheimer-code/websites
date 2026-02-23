"""
Scheduled campaigns: multi-area runs with PST send window (6 AM–11 PM).

Same strategy as single-area pipeline: source → enrich → Touch 1,
then drip Touch 2 (Day 3) and Touch 3 email (Day 7).
"""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from clawbot.integrations.lead_gen.pipeline import run_pipeline

logger = logging.getLogger(__name__)

PST = ZoneInfo("America/Los_Angeles")
SEND_START_HOUR = 6   # 6 AM PST
SEND_END_HOUR = 23    # 11 PM PST (inclusive: up to 10:59:59 PM)

# Campaign: electricians in Morgan Hill and South Bay CA (same strategy: leads + emails)
# Uses a separate Google Sheets tab so these leads don't mix with the main "Leads" tab.
CAMPAIGN_ELECTRICIAN_MORGAN_HILL_SOUTH_BAY = {
    "id": "electrician_morgan_hill_south_bay",
    "category": "electrician",
    "areas": ["Morgan Hill CA", "South Bay CA"],
    "sheet_tab": "Leads - Electrician South Bay",
    "description": "Electricians in Morgan Hill and South Bay CA, 6 AM–11 PM PST",
}

# Campaign: pool cleaners in Morgan Hill and South Bay CA (separate tab, same strategy)
CAMPAIGN_POOL_CLEANER_MORGAN_HILL_SOUTH_BAY = {
    "id": "pool_cleaner_morgan_hill_south_bay",
    "category": "pool cleaner",
    "areas": ["Morgan Hill CA", "South Bay CA"],
    "sheet_tab": "Leads - Pool Cleaner South Bay",
    "description": "Pool service professionals in Morgan Hill and South Bay CA, 6 AM–11 PM PST",
}


def is_within_send_window_pst() -> bool:
    """True if current time is between 6 AM and 11 PM PST (inclusive of 11 PM)."""
    now = datetime.now(PST).time()
    start = datetime.strptime(f"{SEND_START_HOUR:02d}:00", "%H:%M").time()
    # 11 PM PST = up to 23:59:59
    end = datetime.strptime(f"{SEND_END_HOUR:02d}:59", "%H:%M").time()
    return start <= now <= end


async def run_campaign(campaign_id: str, *, skip_time_check: bool = False) -> dict:
    """
    Run a predefined campaign (multiple areas, one category).
    If skip_time_check is False, only runs when current time is 6 AM–11 PM PST.
    Returns combined summary for all areas.
    """
    if campaign_id == "electrician_morgan_hill_south_bay":
        config = CAMPAIGN_ELECTRICIAN_MORGAN_HILL_SOUTH_BAY
    elif campaign_id == "pool_cleaner_morgan_hill_south_bay":
        config = CAMPAIGN_POOL_CLEANER_MORGAN_HILL_SOUTH_BAY
    else:
        raise ValueError(f"Unknown campaign: {campaign_id}")

    if not skip_time_check and not is_within_send_window_pst():
        now_pst = datetime.now(PST).strftime("%H:%M %Z")
        return {
            "status": "skipped",
            "reason": "outside_send_window",
            "campaign_id": campaign_id,
            "window": f"{SEND_START_HOUR}:00–{SEND_END_HOUR}:00 PST",
            "current_time_pst": now_pst,
            "message": f"Campaign runs only 6 AM–11 PM PST. Current time: {now_pst}.",
        }

    category = config["category"]
    areas = config["areas"]
    sheet_tab = config.get("sheet_tab")
    summaries = []

    for area in areas:
        try:
            summary = await run_pipeline(area=area, category=category, sheet_tab=sheet_tab)
            summaries.append(summary)
        except Exception as exc:
            logger.exception(f"Campaign area '{area}' failed: {exc}")
            summaries.append({
                "area": area,
                "category": category,
                "error": str(exc),
            })

    return {
        "status": "completed",
        "campaign_id": campaign_id,
        "category": category,
        "areas": areas,
        "sheet_tab": sheet_tab,
        "summaries": summaries,
        "window": f"{SEND_START_HOUR}:00–{SEND_END_HOUR}:00 PST",
    }


def main():
    """CLI entry: run electrician Morgan Hill + South Bay campaign (for cron)."""
    import argparse
    import json
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run lead-gen campaign (6 AM–11 PM PST)")
    parser.add_argument(
        "--campaign",
        default="electrician_morgan_hill_south_bay",
        help="Campaign ID",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even outside 6 AM–11 PM PST",
    )
    args = parser.parse_args()
    result = asyncio.run(run_campaign(args.campaign, skip_time_check=args.force))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
