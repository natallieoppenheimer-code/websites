# Websites strategy: audit → show the alternative

Use the audit to show prospects **the art of the possible**: we uncover badly run sites and poor SEO, then offer to **rebuild their website with proper SEO** so they can see the alternative.

## Flow

1. **Prospect** visits the audit dashboard (e.g. https://websites-natalie.onrender.com/audit/dashboard) and enters their site URL.
2. **Audit** runs and returns insights (missing title, weak meta, broken headings, etc.) and solutions, plus a “where we can get you” note.
3. **CTA** — “See the art of the possible”: they enter business name, email, (optional) phone and click **“Show me my SEO alternative”**.
4. They’re **registered** in the Website Customers sheet (same Google Sheet as lead-gen, tab **Website Customers**).
5. **You** rebuild their site with SEO (on Render or their host), then:
   - Update the row: set **Status** to `demo_built` and **Alternative Site URL** to the rebuilt demo link.
   - Share that link so they can compare **before (current site) vs after (your rebuild)**.

Result: multiple customers/prospects in one place; each has their current URL, audit snapshot, and (when you’ve built it) their alternative demo URL.

## Registry: Website Customers sheet

- **Sheet:** Same as lead-gen (`LEAD_GEN_SHEET_ID`), tab **Website Customers**.
- **Columns:** ID, Business Name, Contact Email, Contact Phone, Current Site URL, Audit Score, Audit Date, Status, Alternative Site URL, Created At, Notes.
- **Status:** `prospect` → `demo_built` → `live` (or `lost`).

When you build a customer’s SEO alternative:

- In the sheet: set **Status** to `demo_built`, **Alternative Site URL** to the demo link (e.g. `https://acme-demo.onrender.com` or a path on your domain).
- Or call the API: `PATCH /website-customers/{id}` with `{"status": "demo_built", "alternative_site_url": "https://..."}`.

Then you can send the prospect: “Here’s your current site [Current Site URL] vs the alternative we built [Alternative Site URL].”

## API

| Endpoint | Purpose |
|----------|---------|
| `POST /website-customers/register` | Register a prospect (from the audit CTA form). |
| `GET /website-customers` | List all website customers (for internal use). |
| `PATCH /website-customers/{customer_id}` | Update status, Alternative Site URL, or notes. |

## Multiple websites for multiple customers

- **One audit product** for everyone; each prospect gets one (or more) entries in the registry.
- **One rebuilt “alternative” per customer** (or per site if they have several): you build it, set **Alternative Site URL**, and use that to show before/after.
- Scaling: keep using the same Sheet and tab; optionally add a simple internal page that lists customers and their alternative URLs for quick copy-paste when following up.
