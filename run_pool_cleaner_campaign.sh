#!/usr/bin/env bash
# Run pool cleaner campaign (Morgan Hill + South Bay CA), 6 AM–11 PM PST.
# Same strategy: source leads → enrich → Touch 1; drip Touch 2 (Day 3), Touch 3 email (Day 7).
# Leads go to a separate tab: "Leads - Pool Cleaner South Bay".
# Schedule with cron (e.g. 6 AM, 12 PM, 6 PM PST):
#   0 6 * * * /path/to/dev/run_pool_cleaner_campaign.sh >> /path/to/dev/clawbot.log 2>&1

set -e
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"
python -m clawbot.integrations.lead_gen.campaigns --campaign pool_cleaner_morgan_hill_south_bay "$@"
