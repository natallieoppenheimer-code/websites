"""
Scrape the California Secretary of State BizFile website to find
the registered agent (owner) for a business entity.

BizFile is behind Incapsula bot-protection AND requires Okta login.
Both protections are bypassed by using a real Chromium browser (Playwright)
that logs in once, then reuses its session for subsequent searches.

Session persistence: we store Playwright browser state (cookies + localStorage)
to /tmp/bizfile_session/ so we only need to log in once per ~hour.

Environment variables required:
  BIZFILE_EMAIL     — BizFile account email
  BIZFILE_PASSWORD  — BizFile account password
  PLAYWRIGHT_BROWSERS_PATH — path to installed Chromium (set automatically)

If credentials are absent, BizFileResult(found=False) is returned and the
pipeline falls back to the business phone from the lead-gen API.
"""
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

# Force correct Chromium path before any Playwright import
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/Users/paulocfborges/Library/Caches/ms-playwright"

logger = logging.getLogger(__name__)

BIZFILE_URL  = "https://bizfileonline.sos.ca.gov/search/business"
SESSION_FILE = Path("/tmp/bizfile_session/state.json")
SESSION_TTL  = 50 * 60   # 50 minutes

BIZFILE_EMAIL    = os.getenv("BIZFILE_EMAIL", "")
BIZFILE_PASSWORD = os.getenv("BIZFILE_PASSWORD", "")

PAGE_TIMEOUT    = 35_000
ELEMENT_TIMEOUT = 20_000

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class BizFileResult:
    owner_name:    str  = ""
    owner_city:    str  = ""
    owner_state:   str  = "CA"
    entity_status: str  = ""
    found:         bool = False


# ── Session cache ─────────────────────────────────────────────────────────────

def _session_valid() -> bool:
    try:
        if not SESSION_FILE.exists():
            return False
        meta = SESSION_FILE.with_suffix(".meta.json")
        if not meta.exists():
            return False
        data = json.loads(meta.read_text())
        return data.get("saved_at", 0) + SESSION_TTL > time.time()
    except Exception:
        return False


def _save_session_meta() -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    meta = SESSION_FILE.with_suffix(".meta.json")
    meta.write_text(json.dumps({"saved_at": time.time()}))


def _invalidate_session() -> None:
    for f in (SESSION_FILE, SESSION_FILE.with_suffix(".meta.json")):
        try:
            f.unlink()
        except FileNotFoundError:
            pass


# ── Playwright helpers ────────────────────────────────────────────────────────

async def _make_browser(pw):
    """Launch headless Chromium with stealth-friendly settings."""
    return await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
    )


async def _make_context(browser, load_state: bool = False):
    """Create a browser context, optionally restoring saved session."""
    if load_state and SESSION_FILE.exists():
        try:
            ctx = await browser.new_context(
                storage_state=str(SESSION_FILE),
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )
            return ctx
        except Exception as exc:
            logger.debug(f"Failed to load session state: {exc}")

    return await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )


async def _login(browser) -> bool:
    """
    Open BizFile, click Login, fill Okta credentials, wait for redirect back.
    Saves session state to SESSION_FILE on success.
    Returns True on success.
    """
    logger.info("BizFile: starting login via Playwright...")
    ctx = await _make_context(browser, load_state=False)
    page = await ctx.new_page()
    try:
        await page.goto(BIZFILE_URL, wait_until="load", timeout=PAGE_TIMEOUT)

        # Click Login
        await page.click("button:has-text('Login')", timeout=ELEMENT_TIMEOUT)

        # Wait for Okta
        await page.wait_for_url("**/idm.sos.ca.gov/**", timeout=PAGE_TIMEOUT)
        logger.info("BizFile: Okta login page loaded.")

        # Fill credentials
        await page.fill("input[name='identifier']", BIZFILE_EMAIL, timeout=ELEMENT_TIMEOUT)
        await page.fill("input[name='credentials.passcode']", BIZFILE_PASSWORD, timeout=ELEMENT_TIMEOUT)
        await page.click("input[type='submit']", timeout=ELEMENT_TIMEOUT)

        # Wait to land back on BizFile
        await page.wait_for_url("**/bizfileonline.sos.ca.gov/**", timeout=PAGE_TIMEOUT)
        await page.wait_for_load_state("load", timeout=PAGE_TIMEOUT)
        await asyncio.sleep(2)

        logger.info(f"BizFile: login successful. URL: {page.url}")

        # Save session state (cookies + localStorage)
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        await ctx.storage_state(path=str(SESSION_FILE))
        _save_session_meta()
        return True

    except Exception as exc:
        logger.warning(f"BizFile login failed: {exc}")
        return False
    finally:
        await ctx.close()


async def _search_in_browser(browser, business_name: str) -> BizFileResult:
    """
    Use the browser (with active session) to search BizFile and
    call the search API from within the browser context (bypasses Incapsula).
    """
    ctx = await _make_context(browser, load_state=True)
    page = await ctx.new_page()
    try:
        await page.goto(BIZFILE_URL, wait_until="load", timeout=PAGE_TIMEOUT)
        await asyncio.sleep(1)

        # Verify we're still logged in
        auth_result = await page.evaluate(
            "() => fetch('/api/Auth').then(r => r.text())"
        )
        logger.debug(f"BizFile auth check: {auth_result}")
        if "false" in str(auth_result).lower():
            logger.info("BizFile: session expired, re-login needed.")
            _invalidate_session()
            return BizFileResult()

        # Call the search API from INSIDE the browser (bypasses Incapsula)
        search_result = await page.evaluate(
            """async (name) => {
                try {
                    const resp = await fetch('/api/Records/businesssearch', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
                        body: JSON.stringify({
                            SEARCH_VALUE: name,
                            SEARCH_FILTER_TYPE_ID: '0',
                            SEARCH_TYPE_ID: '1',
                            FILING_TYPE_ID: '0',
                            STATUS_ID: '0',
                            RETURN_COUNT: 10,
                            STARTING_ROW: 1
                        })
                    });
                    return {status: resp.status, body: await resp.text()};
                } catch(e) {
                    return {status: 0, body: String(e)};
                }
            }""",
            business_name,
        )

        status = search_result.get("status", 0)
        body   = search_result.get("body", "")
        logger.debug(f"BizFile search status={status}, body_preview={body[:200]}")

        if status != 200:
            logger.info(f"BizFile search returned {status} for '{business_name}'")
            if status in (401, 403):
                _invalidate_session()
            return BizFileResult()

        data = json.loads(body)
        rows = data.get("rows", data if isinstance(data, list) else [])
        if not rows:
            logger.info(f"BizFile: no results for '{business_name}'")
            return BizFileResult()

        logger.debug(f"BizFile: {len(rows)} results. Keys: {list(rows[0].keys())}")

        # Pick best matching entity
        entity = _pick_entity(rows, business_name)
        entity_id = (
            entity.get("ENTITY_ID") or entity.get("ID") or entity.get("id") or ""
        )
        logger.info(f"BizFile: matched entity_id={entity_id} name={entity.get('SEARCH_FILTER_TYPE_DESCR') or entity.get('NAME','?')}")

        # Fetch detail from within the browser
        result = BizFileResult()
        if entity_id:
            detail_result = await page.evaluate(
                """async (eid) => {
                    try {
                        const resp = await fetch('/api/FilingDetail/business/' + eid + '/false', {
                            headers: {'Accept': 'application/json'}
                        });
                        return {status: resp.status, body: await resp.text()};
                    } catch(e) {
                        return {status: 0, body: String(e)};
                    }
                }""",
                str(entity_id),
            )
            d_status = detail_result.get("status", 0)
            d_body   = detail_result.get("body", "")
            logger.debug(f"BizFile detail status={d_status}, preview={d_body[:300]}")
            if d_status == 200:
                try:
                    detail = json.loads(d_body)
                    result = _extract_owner(detail)
                except Exception as exc:
                    logger.debug(f"Detail parse error: {exc}")

        # Fall back to parsing the search row itself
        if not result.found:
            result = _extract_owner(entity)

        if result.found:
            logger.info(
                f"BizFile: '{business_name}' → {result.owner_name} "
                f"({result.owner_city}, {result.owner_state})"
            )
        else:
            logger.info(f"BizFile: owner not found for '{business_name}'. Entity: {json.dumps(entity)[:300]}")

        return result

    except Exception as exc:
        logger.warning(f"BizFile browser search error for '{business_name}': {exc}")
        return BizFileResult()
    finally:
        await ctx.close()


# ── Public entry point ────────────────────────────────────────────────────────

async def lookup_owner(business_name: str) -> BizFileResult:
    """
    Look up the registered owner/agent for *business_name* on CA SOS BizFile.

    Requires BIZFILE_EMAIL and BIZFILE_PASSWORD in the environment.
    Returns BizFileResult(found=False) if credentials are missing or lookup fails.
    """
    if not (BIZFILE_EMAIL and BIZFILE_PASSWORD):
        logger.info("BizFile: no credentials — skipping owner lookup.")
        return BizFileResult()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: playwright install chromium")
        return BizFileResult()

    try:
        async with async_playwright() as pw:
            browser = await _make_browser(pw)
            try:
                return await _login_and_search(browser, business_name)
            finally:
                await browser.close()
    except Exception as exc:
        logger.warning(f"BizFile Playwright error for '{business_name}': {exc}")
        return BizFileResult()


async def _login_and_search(browser, business_name: str) -> BizFileResult:
    """
    Login and search in the SAME browser context so auth tokens are intact.
    Reuses a saved session if still valid.
    """
    # Try with saved session first (fast path — no re-login)
    if _session_valid():
        result = await _search_in_browser(browser, business_name)
        if not result.found and not _session_valid():
            pass  # fall through to re-login
        else:
            return result

    # Need to (re)login
    ctx = await _make_context(browser, load_state=False)
    page = await ctx.new_page()
    try:
        # ── Step 1: Navigate & login ──────────────────────────────────────────
        await page.goto(BIZFILE_URL, wait_until="load", timeout=PAGE_TIMEOUT)
        await page.click("button:has-text('Login')", timeout=ELEMENT_TIMEOUT)
        await page.wait_for_url("**/idm.sos.ca.gov/**", timeout=PAGE_TIMEOUT)

        await page.fill("input[name='identifier']", BIZFILE_EMAIL, timeout=ELEMENT_TIMEOUT)
        await page.fill("input[name='credentials.passcode']", BIZFILE_PASSWORD, timeout=ELEMENT_TIMEOUT)
        await page.click("input[type='submit']", timeout=ELEMENT_TIMEOUT)

        # Wait for the app to finish processing the Okta callback
        await page.wait_for_url("**/bizfileonline.sos.ca.gov/**", timeout=PAGE_TIMEOUT)
        # Give the React app time to exchange the code and store tokens
        await page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT)
        await asyncio.sleep(2)

        # Verify auth
        auth_val = await page.evaluate("() => fetch('/api/Auth').then(r => r.text())")
        logger.info(f"BizFile post-login auth check: {auth_val}")

        # Save session for next lookup
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        await ctx.storage_state(path=str(SESSION_FILE))
        _save_session_meta()

        # ── Step 2: Search in the SAME page (same context = same auth) ────────
        result = await _do_search(page, business_name)
        return result

    except Exception as exc:
        logger.warning(f"BizFile login+search failed for '{business_name}': {exc}")
        return BizFileResult()
    finally:
        await ctx.close()


async def _do_search(page, business_name: str) -> BizFileResult:
    """
    Perform BizFile search using full UI interaction on an already-authenticated page.
    Navigates to the search page, types the business name, clicks Search, clicks the
    first result, then parses the detail panel — no fetch() calls, so Incapsula's
    AJAX protection is bypassed.
    """
    from playwright.async_api import TimeoutError as PWTimeout

    try:
        # Navigate to search page (we may already be there, but ensure fresh state)
        if "/search/business" not in page.url:
            await page.goto(BIZFILE_URL, wait_until="load", timeout=PAGE_TIMEOUT)
            await asyncio.sleep(1)

        # Intercept the search API response via network events so we get the JSON
        # even though Incapsula blocks direct fetch() calls
        api_data: list = []

        async def handle_response(response):
            if "/api/Records/businesssearch" in response.url and response.status == 200:
                try:
                    body = await response.text()
                    data = json.loads(body)
                    rows = data.get("rows", data if isinstance(data, list) else [])
                    api_data.extend(rows)
                    logger.info(f"BizFile: intercepted {len(rows)} search rows")
                except Exception as exc:
                    logger.debug(f"BizFile intercept parse error: {exc}")

        page.on("response", handle_response)

        # Type into search box and click search button
        search_box = await page.wait_for_selector("input[type='text']", timeout=ELEMENT_TIMEOUT)
        await search_box.fill("")
        await search_box.type(business_name, delay=40)
        await page.click("button[aria-label='Execute search']", timeout=ELEMENT_TIMEOUT)

        # Wait for results to appear in the DOM
        await asyncio.sleep(3)
        try:
            await page.wait_for_selector(
                "table tbody tr, [class*='result'], [class*='row']",
                timeout=10_000
            )
        except PWTimeout:
            pass

        page.remove_listener("response", handle_response)

        if not api_data:
            # Fall back: try to parse results from the DOM
            logger.info(f"BizFile: no API intercept data; trying DOM parse for '{business_name}'")
            body_text = await page.inner_text("body")
            result = _parse_page_text(body_text, business_name)
            return result

        entity = _pick_entity(api_data, business_name)
        entity_id = entity.get("ENTITY_ID") or entity.get("ID") or entity.get("id") or ""
        logger.info(f"BizFile: entity_id={entity_id}, keys={list(entity.keys())[:10]}")

        # Click the first matching table row to load detail panel
        detail_data: list = []

        async def handle_detail(response):
            if "/api/FilingDetail" in response.url and response.status == 200:
                try:
                    body = await response.text()
                    detail_data.append(json.loads(body))
                    logger.info(f"BizFile: intercepted detail for entity_id={entity_id}")
                except Exception as exc:
                    logger.debug(f"Detail parse: {exc}")

        page.on("response", handle_detail)

        try:
            rows = page.locator("table tbody tr")
            count = await rows.count()
            if count > 0:
                await rows.first.click()
                await asyncio.sleep(3)
        except Exception:
            pass

        page.remove_listener("response", handle_detail)

        result = BizFileResult()
        if detail_data:
            result = _extract_owner(detail_data[0])
        if not result.found:
            result = _extract_owner(entity)

        if result.found:
            logger.info(f"BizFile: '{business_name}' → {result.owner_name} ({result.owner_city}, {result.owner_state})")
        else:
            # Last resort: parse the full page body text
            body_text = await page.inner_text("body")
            logger.debug(f"BizFile page text (first 500): {body_text[:500]}")
            result = _parse_page_text(body_text, business_name)

        return result

    except Exception as exc:
        logger.warning(f"BizFile _do_search error for '{business_name}': {exc}")
        return BizFileResult()


def _parse_page_text(text: str, business_name: str) -> BizFileResult:
    """
    Parse the rendered page text for registered agent info.
    BizFile shows sections like:
        Registered Agent
        CHRIS JOHNSON
        2108 N ST STE C, SACRAMENTO, CA
    """
    result = BizFileResult()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    AGENT_MARKERS = [
        "registered agent", "agent name", "agent authorized",
        "corporate agent", "statutory agent",
    ]

    for i, line in enumerate(lines):
        lower = line.lower()
        if any(m in lower for m in AGENT_MARKERS):
            for j in range(i + 1, min(i + 8, len(lines))):
                candidate = lines[j].strip()
                if _looks_like_name(candidate):
                    result.owner_name = candidate.title()
                    # Try next lines for city/state
                    for k in range(j + 1, min(j + 5, len(lines))):
                        city, state = _parse_city_state(lines[k])
                        if city:
                            result.owner_city  = city
                            result.owner_state = state
                            break
                    result.found = True
                    return result
    return result


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _pick_entity(rows: list, name: str) -> dict:
    """Return the best-matching entity row."""
    name_lower = name.lower()
    # Prefer active entities whose name matches
    for row in rows:
        row_name = str(row.get("NAME", "") or row.get("SEARCH_FILTER_TYPE_DESCR", "")).lower()
        status   = str(row.get("STATUS_TYPE", {}).get("DESCR", "") or row.get("STATUS", "")).lower()
        if name_lower in row_name and "active" in status:
            return row
    for row in rows:
        status = str(row.get("STATUS_TYPE", {}).get("DESCR", "") or row.get("STATUS", "")).lower()
        if "active" in status:
            return row
    return rows[0]


def _extract_owner(data: dict) -> BizFileResult:
    """Parse a BizFile entity detail or search-row dict for agent info."""
    result = BizFileResult()
    if not data:
        return result

    # Status
    result.entity_status = (
        data.get("STATUS_TYPE", {}).get("DESCR", "")
        or data.get("STATUS", "")
        or ""
    )

    # Known agent section keys in BizFile API
    for key in ("AGEN", "AGENT", "PRINCIPAL", "OFFICER", "MEMBER", "MANAGER"):
        section = data.get(key, [])
        if isinstance(section, dict):
            section = [section]
        for item in section:
            name = _pick_name(item)
            if name:
                addr = item.get("ADDRESS", {}) or {}
                city  = (addr.get("CITY") or item.get("CITY") or "").strip().title()
                state = (addr.get("STATE") or item.get("STATE") or "CA").strip()
                result.owner_name  = name
                result.owner_city  = city
                result.owner_state = state or "CA"
                result.found       = True
                return result

    # Deep-scan all string values in the JSON for a name-like string
    result = _deep_scan(data)
    return result


def _pick_name(item: dict) -> str:
    """Extract a person name from an agent/officer dict."""
    # Explicit full-name field
    for k in ("NAME", "AGENT_NAME", "FULL_NAME"):
        v = str(item.get(k) or "").strip()
        if v and _looks_like_name(v):
            return v.title()
    # First + Last
    first = str(item.get("FIRST_NAME") or "").strip()
    last  = str(item.get("LAST_NAME")  or "").strip()
    if first or last:
        name = f"{first} {last}".strip()
        if _looks_like_name(name):
            return name.title()
    return ""


def _deep_scan(data: dict) -> BizFileResult:
    """Recursively scan a dict for agent-related name clues."""
    result = BizFileResult()
    text = json.dumps(data)

    AGENT_KEYWORDS = ("agent", "registered", "principal", "officer", "member", "manager")
    lines = text.replace(",", "\n").replace("{", "\n").replace("}", "\n").splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip().strip('"')
        if any(kw in stripped.lower() for kw in AGENT_KEYWORDS):
            for j in range(i + 1, min(i + 15, len(lines))):
                candidate = lines[j].strip().strip('"').strip()
                if _looks_like_name(candidate):
                    result.owner_name = candidate.title()
                    result.found = True
                    # Look for city in nearby lines
                    for k in range(j + 1, min(j + 8, len(lines))):
                        city_line = lines[k].strip().strip('"').strip()
                        city, state = _parse_city_state(city_line)
                        if city:
                            result.owner_city  = city
                            result.owner_state = state
                            break
                    return result
    return result


def _looks_like_name(text: str) -> bool:
    if not text or len(text) < 3 or len(text) > 60:
        return False
    words = text.split()
    if not (1 <= len(words) <= 5):
        return False
    if any(ch.isdigit() for ch in text):
        return False
    SKIP = {"true","false","null","none","ca","llc","inc","corp","ltd","co","the",
            "and","agent","registered","authorized","employee","principal","officer",
            "member","manager","active","inactive","suspended","dissolved"}
    if text.strip().lower() in SKIP:
        return False
    return sum(1 for w in words if w.replace(".","").replace(",","").isalpha()) >= 1


def _parse_city_state(location: str) -> tuple[str, str]:
    """Parse 'SACRAMENTO, CA 95816' → ('Sacramento', 'CA')."""
    import re
    if not location:
        return "", "CA"
    # Look for a 2-letter state code
    m = re.search(r'\b([A-Z]{2})\b', location)
    if m:
        state = m.group(1)
        before = location[:m.start()].strip().rstrip(",").strip()
        # Remove leading street number / zip
        before = re.sub(r'^\d+\s*', '', before).strip()
        return before.title(), state
    return "", "CA"
