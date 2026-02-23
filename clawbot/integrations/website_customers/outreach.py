"""
Natalie's outreach to website audit customers.

After we audit their site and build the demo, Natalie sends:
  1. SMS  — score + issues found + link to full report + demo link
  2. Email — full HTML email with findings summary + report + demo

Both go out immediately when a prospect registers.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

RENDER_BASE = os.getenv("RENDER_EXTERNAL_URL", "https://websites-pilv.onrender.com")
NATALIE_PHONE = "+16692587531"
TEXTLINK_API_KEY = os.getenv("TEXTLINK_API_KEY", "")
TEXTLINK_FROM = os.getenv("TEXTLINK_FROM_NUMBER", "+16692587531")


def _is_dry_run() -> bool:
    return os.getenv("LEAD_GEN_DRY_RUN", "").strip() not in ("", "0", "false")


# ── SMS ───────────────────────────────────────────────────────────────────────

def send_audit_sms(
    to_phone: str,
    business_name: str,
    score: Optional[float],
    findings_count: int,
    report_url: str,
    demo_url: str,
) -> bool:
    """Send audit result SMS from Natalie. Returns True on success."""
    if not to_phone:
        logger.warning("[outreach] No phone number — skipping SMS")
        return False

    score_str = f"{score:.0f}/100" if score is not None else "reviewed"
    issues_str = f"{findings_count} issue{'s' if findings_count != 1 else ''}" if findings_count else "no issues"

    msg = (
        f"Hi! This is Natalie from Equestro Labs. "
        f"I just audited {business_name}'s website — score: {score_str} ({issues_str} found). "
        f"Full report: {report_url} | "
        f"Free rebuilt demo: {demo_url} | "
        f"Questions? Text me: {NATALIE_PHONE}"
    )

    if _is_dry_run():
        logger.info("[outreach][DRY RUN] SMS to %s: %s", to_phone, msg[:80])
        return True

    try:
        import httpx
        digits = "".join(c for c in to_phone if c.isdigit())
        if len(digits) == 10:
            digits = "1" + digits
        e164 = "+" + digits if not digits.startswith("+") else digits

        resp = httpx.post(
            "https://app.textlinksms.com/api/send",
            json={"apiKey": TEXTLINK_API_KEY, "phone": e164, "message": msg},
            timeout=10.0,
        )
        if resp.status_code == 200:
            logger.info("[outreach] SMS sent to %s for %s", e164, business_name)
            return True
        logger.error("[outreach] SMS failed (%s): %s", resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        logger.error("[outreach] SMS error: %s", exc)
        return False


# ── Email ─────────────────────────────────────────────────────────────────────

def send_audit_email(
    to_email: str,
    business_name: str,
    score: Optional[float],
    findings: list,
    report_url: str,
    demo_url: str,
) -> bool:
    """Send audit result email from Natalie. Returns True on success."""
    if not to_email:
        to_email = os.getenv("NATALIE_EMAIL", "natalie@equestrolabs.com")
        logger.warning("[outreach] No contact email — sending demo copy to Natalie")

    score_str = f"{score:.0f}/100" if score is not None else "reviewed"

    # Build findings rows for the email table
    rows = ""
    sev_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
    for f in findings:
        emoji = sev_emoji.get(f.get("severity", "info"), "•")
        rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 12px;font-size:13px;">{emoji} {f.get("message","")}</td>
          <td style="padding:10px 12px;font-size:13px;color:#374151;">{f.get("solution","")}</td>
        </tr>"""

    demo_block = ""
    if demo_url:
        demo_block = f"""
      <div style="background:#1e40af;border-radius:12px;padding:24px;text-align:center;margin:24px 0;">
        <p style="color:#fff;font-size:16px;font-weight:700;margin:0 0 12px;">
          👀 We already built your free demo site!
        </p>
        <a href="{demo_url}" style="display:inline-block;background:#f97316;color:#fff;font-weight:700;padding:12px 28px;border-radius:8px;text-decoration:none;font-size:15px;">
          View {business_name} — Rebuilt →
        </a>
      </div>"""

    html_body = f"""
<html><body style="font-family:-apple-system,sans-serif;background:#f9fafb;padding:0;margin:0;">
<div style="max-width:600px;margin:32px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8);padding:28px 32px;color:#fff;">
    <p style="font-size:12px;opacity:.7;margin:0 0 4px;text-transform:uppercase;letter-spacing:1px;">Free Website Audit from Equestro Labs</p>
    <h1 style="font-size:22px;font-weight:800;margin:0;">{business_name} — SEO Report</h1>
    <p style="opacity:.8;font-size:14px;margin:8px 0 0;">Score: <strong>{score_str}</strong> · {len(findings)} issue{"s" if len(findings) != 1 else ""} found</p>
  </div>

  <div style="padding:28px 32px;">
    <p style="color:#374151;font-size:15px;margin:0 0 20px;">
      Hi! I'm <strong>Natalie</strong> from Equestro Labs. I ran a free SEO audit on <strong>{business_name}</strong>'s website and wanted to share the results — along with a free demo of what the site could look like with proper SEO.
    </p>

    {demo_block}

    <!-- Report link -->
    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:16px 20px;margin-bottom:24px;text-align:center;">
      <p style="font-size:14px;color:#1e40af;font-weight:600;margin:0 0 8px;">📊 Full interactive report</p>
      <a href="{report_url}" style="color:#1d4ed8;font-size:14px;">{report_url}</a>
    </div>

    <!-- Findings table -->
    {"<h2 style='font-size:16px;font-weight:700;color:#111;margin:0 0 12px;'>Issues Found</h2><table width='100%' cellpadding='0' cellspacing='0' style='border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;'><thead><tr style='background:#f9fafb;'><th style='padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;'>Issue</th><th style='padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;'>How to Fix</th></tr></thead><tbody>" + rows + "</tbody></table>" if findings else "<p style='color:#16a34a;font-weight:600;'>✅ No issues found — this site passes all SEO checks!</p>"}

    <div style="margin-top:28px;padding-top:24px;border-top:1px solid #f3f4f6;text-align:center;">
      <p style="color:#374151;font-size:14px;margin:0 0 16px;">
        Ready to fix these issues and launch your new site? I'm happy to walk you through it — no jargon, no pressure.
      </p>
      <a href="mailto:natalie@equestrolabs.com" style="display:inline-block;background:#1e40af;color:#fff;font-weight:700;padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px;margin-right:8px;">
        Reply to this email
      </a>
      <a href="sms:+16692587531" style="display:inline-block;background:#16a34a;color:#fff;font-weight:700;padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px;">
        Text Natalie
      </a>
    </div>
  </div>

  <div style="background:#f9fafb;padding:16px 32px;border-top:1px solid #f3f4f6;">
    <p style="color:#9ca3af;font-size:12px;margin:0;text-align:center;">
      Natalie · Equestro Labs · natalie@equestrolabs.com · {NATALIE_PHONE}<br/>
      <a href="{report_url}" style="color:#9ca3af;">View your full report</a>
    </p>
  </div>
</div>
</body></html>"""

    text_body = (
        f"Hi, I'm Natalie from Equestro Labs.\n\n"
        f"I audited {business_name}'s website — score: {score_str}, {len(findings)} issue(s) found.\n\n"
        f"Full report: {report_url}\n"
        f"Free rebuilt demo: {demo_url}\n\n"
        f"Reply to this email or text me at {NATALIE_PHONE} to discuss next steps.\n\n"
        f"Best,\nNatalie\nEquestro Labs | equestrolabs.com"
    )

    subject = f"Your free website audit — {business_name} scored {score_str}"

    if _is_dry_run():
        logger.info("[outreach][DRY RUN] Email to %s — %s", to_email, subject)
        return True

    try:
        from clawbot.integrations.natalie_email import NatalieEmailService
        svc = NatalieEmailService("natalie@equestrolabs.com")
        result = svc.send_message(
            to=to_email,
            subject=subject,
            body=text_body,
            html_body=html_body,
        )
        logger.info("[outreach] Email sent to %s for %s", to_email, business_name)
        return bool(result)
    except Exception as exc:
        logger.error("[outreach] Email error: %s", exc)
        return False


# ── Combined ──────────────────────────────────────────────────────────────────

def send_audit_outreach(
    business_name: str,
    slug: str,
    score: Optional[float],
    findings: list,
    demo_url: str,
    contact_email: str = "",
    contact_phone: str = "",
) -> dict:
    """
    Send both SMS and email from Natalie after an audit + demo build.
    Returns {sms_sent, email_sent}.
    """
    report_url = f"{RENDER_BASE}/audit/report/{slug}"
    findings_count = len(findings)

    sms_ok = send_audit_sms(
        to_phone=contact_phone,
        business_name=business_name,
        score=score,
        findings_count=findings_count,
        report_url=report_url,
        demo_url=demo_url,
    )

    email_ok = send_audit_email(
        to_email=contact_email,
        business_name=business_name,
        score=score,
        findings=findings,
        report_url=report_url,
        demo_url=demo_url,
    )

    return {"sms_sent": sms_ok, "email_sent": email_ok, "report_url": report_url}
