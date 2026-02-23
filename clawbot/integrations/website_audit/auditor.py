"""Website/SEO auditor: fetch URL, parse HTML, run checks, return findings + solutions."""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Timeout and user-agent for fetches (respect robots; no headless)
FETCH_TIMEOUT = 15.0
USER_AGENT = "EquestroLabs-Audit/1.0 (Website audit; +https://equestrolabs.com)"


@dataclass
class Finding:
    """Single audit finding."""
    severity: str  # "critical", "warning", "info"
    category: str  # "seo", "accessibility", "structure", "performance"
    message: str
    solution: str
    element: Optional[str] = None  # e.g. tag or snippet


@dataclass
class AuditReport:
    """Structured audit report for a URL."""
    url: str
    success: bool
    error: Optional[str] = None
    findings: List[Finding] = field(default_factory=list)
    summary_score: Optional[float] = None  # 0–100
    target_note: Optional[str] = None  # "Where we can get you"


def _is_safe_url(url: str) -> bool:
    """Reject non-HTTP(S) and private/localhost URLs."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "::1"):
            return False
        if host.endswith(".local"):
            return False
        # Reject private IP ranges
        if re.match(r"^10\.", host) or re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", host) or re.match(r"^192\.168\.", host):
            return False
        return True
    except Exception:
        return False


def _normalize_url(url: str) -> str:
    """Ensure URL has a scheme."""
    s = url.strip()
    if not s:
        return s
    if not s.startswith(("http://", "https://")):
        return "https://" + s
    return s


async def _fetch_html(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Fetch URL; return (success, html_text, error_message)."""
    try:
        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return True, resp.text, None
    except httpx.TimeoutException as e:
        return False, None, f"Request timed out: {e}"
    except httpx.HTTPStatusError as e:
        return False, None, f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
    except Exception as e:
        return False, None, str(e)


def _run_checks(soup: BeautifulSoup, url: str) -> List[Finding]:
    """Run SEO/structure checks on parsed HTML; return list of findings."""
    findings: List[Finding] = []

    # --- Title ---
    title = soup.find("title")
    title_text = (title.get_text(strip=True) if title else "") or ""
    if not title_text:
        findings.append(Finding(
            severity="critical",
            category="seo",
            message="Missing <title> tag.",
            solution="Add a unique <title> under 60 characters that describes the page.",
            element="<title>",
        ))
    elif len(title_text) > 60:
        findings.append(Finding(
            severity="warning",
            category="seo",
            message=f"Title is too long ({len(title_text)} chars); search engines may truncate it.",
            solution="Shorten the <title> to under 60 characters.",
            element=f"<title>{title_text[:50]}…</title>",
        ))

    # --- Meta description ---
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_content = (meta_desc.get("content", "") if meta_desc else "").strip()
    if not desc_content:
        findings.append(Finding(
            severity="critical",
            category="seo",
            message="Missing <meta name=\"description\">.",
            solution="Add a meta description (150–160 chars) that summarizes the page.",
            element="<meta name=\"description\">",
        ))
    elif len(desc_content) > 160:
        findings.append(Finding(
            severity="warning",
            category="seo",
            message=f"Meta description is too long ({len(desc_content)} chars).",
            solution="Keep the meta description between 150–160 characters.",
            element="<meta name=\"description\" content=\"…\">",
        ))

    # --- Viewport ---
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        findings.append(Finding(
            severity="critical",
            category="seo",
            message="Missing <meta name=\"viewport\">; site may not be mobile-friendly.",
            solution="Add: <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            element="<meta name=\"viewport\">",
        ))

    # --- Heading hierarchy ---
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    h1s = [h for h in headings if h.name == "h1"]
    if not h1s:
        findings.append(Finding(
            severity="critical",
            category="structure",
            message="No <h1> on the page.",
            solution="Add exactly one <h1> that states the main topic of the page.",
            element="<h1>",
        ))
    elif len(h1s) > 1:
        findings.append(Finding(
            severity="warning",
            category="structure",
            message=f"Multiple <h1> tags ({len(h1s)}); use a single main heading.",
            solution="Use one <h1> per page; use <h2>–<h6> for subheadings.",
            element="<h1>",
        ))
    # Check order (e.g. h3 before h2)
    levels = [int(h.name[1]) for h in headings]
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            findings.append(Finding(
                severity="warning",
                category="structure",
                message="Heading levels skip (e.g. h3 after h1); use sequential order.",
                solution="Use headings in order: h1 then h2, then h3, etc.",
                element=f"<{headings[i].name}>",
            ))
            break

    # --- Images without alt ---
    imgs = soup.find_all("img")
    missing_alt = [img for img in imgs if not (img.get("alt") or "").strip()]
    if missing_alt:
        count = len(missing_alt)
        findings.append(Finding(
            severity="warning",
            category="accessibility",
            message=f"{count} image(s) missing alt text.",
            solution="Add descriptive alt attributes to every <img> for accessibility and SEO.",
            element=f"<img> ({count} without alt)",
        ))

    # --- Empty or placeholder links ---
    links = soup.find_all("a", href=True)
    empty_links = [a for a in links if (a.get("href") or "").strip() in ("", "#", "javascript:void(0)")]
    if empty_links:
        findings.append(Finding(
            severity="info",
            category="structure",
            message=f"{len(empty_links)} link(s) with empty or placeholder href.",
            solution="Replace placeholder links with real URLs or use buttons for actions.",
            element="<a href=\"#\">",
        ))

    # --- Canonical ---
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if not canonical:
        findings.append(Finding(
            severity="info",
            category="seo",
            message="No canonical URL set.",
            solution="Add <link rel=\"canonical\" href=\"…\"> to avoid duplicate content issues.",
            element="<link rel=\"canonical\">",
        ))

    # --- Open Graph / Twitter (optional but recommended) ---
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if not og_title:
        findings.append(Finding(
            severity="info",
            category="seo",
            message="No Open Graph (og:title) meta; sharing previews may be poor.",
            solution="Add og:title, og:description, and og:image for better social sharing.",
            element="<meta property=\"og:title\">",
        ))

    return findings


def _score_from_findings(findings: List[Finding]) -> float:
    """Compute a simple 0–100 score from findings (fewer/severity = higher score)."""
    if not findings:
        return 100.0
    penalty = 0.0
    for f in findings:
        if f.severity == "critical":
            penalty += 25
        elif f.severity == "warning":
            penalty += 10
        else:
            penalty += 3
    return max(0.0, min(100.0, 100.0 - penalty))


def _build_report(url: str, success: bool, html: Optional[str], error: Optional[str]) -> AuditReport:
    """Build AuditReport from fetch result and optional HTML."""
    if not success or not html:
        return AuditReport(
            url=url,
            success=False,
            error=error or "Failed to fetch page",
            target_note="With our help we can get your site reachable and then improve SEO and performance.",
        )
    soup = BeautifulSoup(html, "html.parser")
    findings = _run_checks(soup, url)
    score = _score_from_findings(findings)
    target_note = (
        "With our help: fix these issues to reach 90+ SEO health, better rankings, and mobile-friendly results."
    )
    return AuditReport(
        url=url,
        success=True,
        findings=findings,
        summary_score=round(score, 1),
        target_note=target_note,
    )


async def run_audit(url: str) -> AuditReport:
    """
    Run a website/SEO audit on the given URL.
    Returns a structured report with findings, solutions, and summary.
    """
    normalized = _normalize_url(url)
    if not _is_safe_url(normalized):
        return AuditReport(
            url=normalized or url,
            success=False,
            error="Invalid or disallowed URL (use http/https and avoid localhost or private IPs).",
            target_note="With our help we can get your site audited once it is publicly reachable.",
        )
    success, html, err = await _fetch_html(normalized)
    report = _build_report(normalized, success, html, err)
    logger.info(f"Audit for {normalized}: success={report.success}, findings={len(report.findings)}")
    return report


def report_to_dict(report: AuditReport) -> dict:
    """Serialize AuditReport to a JSON-friendly dict for the API."""
    return {
        "url": report.url,
        "success": report.success,
        "error": report.error,
        "findings": [
            {
                "severity": f.severity,
                "category": f.category,
                "message": f.message,
                "solution": f.solution,
                "element": f.element,
            }
            for f in report.findings
        ],
        "summary_score": report.summary_score,
        "target_note": report.target_note,
    }
