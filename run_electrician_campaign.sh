#!/usr/bin/env bash
# Run electrician campaign (Morgan Hill + South Bay CA), 6 AM–11 PM PST.
# Same strategy: source leads → enrich → Touch 1; drip Touch 2 (Day 3), Touch 3 email (Day 7).
# Schedule with cron starting tomorrow, e.g.:
#   0 6,12,18 * * * /path/to/dev/run_electrician_campaign.sh >> /path/to/dev/clawbot.log 2>&1
# (Runs at 6 AM, 12 PM, 6 PM; only runs that do fall in 6–11 PM PST will send.)

set -e
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"
python -m clawbot.integrations.lead_gen.campaigns "$@"
