# Electrician campaign: Morgan Hill + South Bay CA

Campaign for **electricians** in **Morgan Hill CA** and **South Bay CA**, same strategy as the existing lead pipeline:

- **Source** leads from RapidAPI → **Enrich** (BizFile + People Search) → **Touch 1** intro SMS  
- **Touch 2** follow-up SMS (Day 3)  
- **Touch 3** email (Day 7)

Sends only between **6 AM and 11 PM PST** so messages don’t go out at night.

## Start the campaign (starting tomorrow)

### Option 1: Cron (recommended)

Run the campaign on a schedule so it keeps sending leads and drip emails. First run **tomorrow** at 6 AM PST, then a few times per day during the window:

```bash
chmod +x /Users/paulocfborges/Desktop/dev/run_electrician_campaign.sh
```

Add to crontab (`crontab -e`). Example: run at 6 AM, 12 PM, and 6 PM (PST) every day:

```cron
# Electrician Morgan Hill + South Bay — 6 AM, 12 PM, 6 PM (only runs in 6 AM–11 PM PST actually send)
0 6 * * * /Users/paulocfborges/Desktop/dev/run_electrician_campaign.sh >> /Users/paulocfborges/Desktop/dev/clawbot.log 2>&1
0 12 * * * /Users/paulocfborges/Desktop/dev/run_electrician_campaign.sh >> /Users/paulocfborges/Desktop/dev/clawbot.log 2>&1
0 18 * * * /Users/paulocfborges/Desktop/dev/run_electrician_campaign.sh >> /Users/paulocfborges/Desktop/dev/clawbot.log 2>&1
```

Adjust times if your cron uses UTC. PST is UTC-8 (e.g. 6 AM PST = 14:00 UTC in winter).

### Option 2: API (when the API is running)

- **Background:** `POST /leads/campaign/run` (default campaign: `electrician_morgan_hill_south_bay`)  
- **Sync (wait for result):** `POST /leads/campaign/run/sync`  
- To run even outside 6–11 PM PST (e.g. testing): `?skip_time_check=true`

Example:

```bash
curl -X POST "http://localhost:8000/leads/campaign/run"
```

### Option 3: Run once from CLI

From project root:

```bash
export PYTHONPATH="$(pwd)"
python -m clawbot.integrations.lead_gen.campaigns
```

To run outside the time window (e.g. test):

```bash
python -m clawbot.integrations.lead_gen.campaigns --force
```

## Google Sheets

Leads from this campaign are written to a **separate tab** in the same spreadsheet (same `LEAD_GEN_SHEET_ID`):

- **Tab name:** `Leads - Electrician South Bay`

So electrician (Morgan Hill + South Bay) leads stay in their own tab and don’t mix with the main **Leads** tab.

## Summary

| Item | Value |
|------|--------|
| **Category** | electrician |
| **Areas** | Morgan Hill CA, South Bay CA |
| **Sheet tab** | Leads - Electrician South Bay |
| **Send window** | 6 AM–11 PM PST |
| **Strategy** | Same as existing pipeline (leads + Touch 1/2/3) |
