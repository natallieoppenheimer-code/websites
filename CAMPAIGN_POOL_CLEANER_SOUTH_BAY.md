# Pool cleaner campaign: Morgan Hill + South Bay CA

Campaign for **pool service professionals** in **Morgan Hill CA** and **South Bay CA**, same strategy as the electrician campaign:

- **Source** leads from RapidAPI → **Enrich** (BizFile + People Search) → **Touch 1** intro SMS  
- **Touch 2** follow-up SMS (Day 3)  
- **Touch 3** email (Day 7)

Sends only between **6 AM and 11 PM PST**. Leads are stored in a **separate Google Sheets tab**: `Leads - Pool Cleaner South Bay`.

---

## Research: Where software creates massive impact for pool service pros

Outside research (industry reports, pool service software vendors, fleet/route optimization studies) points to these **high-impact pain points** that software can address:

### 1. **Route chaos & scheduling inefficiency**
- **3–5 hours per week** lost to manual route planning; technicians zigzag between neighborhoods.
- One tracked case: **47 extra miles per day** per truck due to poor route sequencing → **$15–20/day in wasted fuel** per vehicle.
- **Seasonal route rebuilds** take **8–12 hours** when done manually; any change (tech out, cancellation) forces rebuilding from scratch.
- **Impact:** Route optimization software can cut planning time by ~95%, reduce drive time 20–30%, and increase territory by ~43% without adding trucks.

### 2. **Double booking & service-window chaos**
- Without smart scheduling, rescheduling rates can reach **~15%**; with precision scheduling (e.g. 2–3 hour service windows per job), rates drop to **under 3%**.
- Dispatcher overhead to constantly fix double-bookings and reshuffle routes: **$20K–40K/year** saved when software handles it.
- **Impact:** AI scheduling that prevents double-bookings and auto-rebalances when techs call out or customers cancel removes most of this cost and stress.

### 3. **Fleet & recurring-route complexity**
- **$50–75 per vehicle per day** in wasted time and fuel from poor routes; can account for **up to 15% of total operational expenses**.
- Recurring routes are hard to adjust when a tech calls in sick or a customer cancels last-minute → inefficiency, fuel costs, and stress.
- **Impact:** Intelligent dispatching with route load balancing, recurring routes that adapt in real time, and automatic rebalancing as new jobs arrive.

### 4. **Rising costs & labor pressure**
- **~74%** of pool pros planned price adjustments in 2024 due to rising costs; **~52%** planned to hire in a tight labor market.
- Technicians stressed by chaotic schedules and wasted drive time → retention and productivity issues.
- **Impact:** Software that saves 20–40 min/day per tech and cuts fuel/wasted miles improves margins and makes the job more manageable.

### 5. **Scheduling rigidity**
- Fixed time slots and manual planning don’t handle emergencies, weather delays, or last-minute changes.
- **Impact:** Systems that set **recurring routes** and **adapt quickly** to absences and cancellations without full rebuilds.

---

## Messaging used in this campaign

Outreach copy is aligned with the above:

- **Touch 1 (SMS):** Eliminate route chaos and double-bookings; AI scheduling that adapts when techs call out or customers cancel, no more rebuilding routes from scratch.
- **Touch 2 (SMS):** Local pool service company rolled out route optimization → cut wasted drive time 20–30% and reschedules significantly.
- **Touch 3 (Email):** Smart scheduling (no double-bookings), route optimization (save 20–40 min/day), automatic dispatch — same value props as other field-service campaigns, framed for pool pros.

---

## How to run the campaign

### Option 1: Cron (recommended)

```bash
chmod +x /Users/paulocfborges/Desktop/dev/run_pool_cleaner_campaign.sh
```

Add to crontab (`crontab -e`), e.g. 6 AM, 12 PM, 6 PM PST:

```cron
# Pool cleaner Morgan Hill + South Bay
0 6 * * * /Users/paulocfborges/Desktop/dev/run_pool_cleaner_campaign.sh >> /Users/paulocfborges/Desktop/dev/clawbot.log 2>&1
0 12 * * * /Users/paulocfborges/Desktop/dev/run_pool_cleaner_campaign.sh >> /Users/paulocfborges/Desktop/dev/clawbot.log 2>&1
0 18 * * * /Users/paulocfborges/Desktop/dev/run_pool_cleaner_campaign.sh >> /Users/paulocfborges/Desktop/dev/clawbot.log 2>&1
```

Adjust for your cron timezone (PST = UTC-8 in winter).

### Option 2: API

- **Background:** `POST /leads/campaign/run?campaign_id=pool_cleaner_morgan_hill_south_bay`
- **Sync:** `POST /leads/campaign/run/sync?campaign_id=pool_cleaner_morgan_hill_south_bay`
- **Outside window (e.g. test):** `?skip_time_check=true`

### Option 3: CLI

From project root:

```bash
export PYTHONPATH="$(pwd)"
python -m clawbot.integrations.lead_gen.campaigns --campaign pool_cleaner_morgan_hill_south_bay
```

With `--force` to run outside 6–11 PM PST.

---

## Summary

| Item | Value |
|------|--------|
| **Category** | pool cleaner |
| **Areas** | Morgan Hill CA, South Bay CA |
| **Sheet tab** | Leads - Pool Cleaner South Bay |
| **Send window** | 6 AM–11 PM PST |
| **Strategy** | Same as electrician campaign (leads + Touch 1/2/3) |
