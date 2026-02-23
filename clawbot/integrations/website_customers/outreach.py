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
    issues_str = f"{findings_count} quick fix{'es' if findings_count != 1 else ''}" if findings_count else "all clear"

    msg = (
        f"Hi! 😊 This is Natalie from Equestro Labs — I hope this finds you well! "
        f"I took a peek at {business_name}'s website and put together a free SEO report just for you "
        f"(score: {score_str}, {issues_str}). "
        f"I also went ahead and built a free demo showing what your site could look like — "
        f"no strings attached, just wanted to show you what's possible! "
        f"Report: {report_url} · Demo: {demo_url} "
        f"Feel free to text me any time: {NATALIE_PHONE} 💙"
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

        # Use the same /send-sms endpoint the rest of Clawbot uses
        clawbot_base = os.getenv("CLAWBOT_BASE_URL", "http://localhost:8000").rstrip("/")
        resp = httpx.post(
            f"{clawbot_base}/send-sms",
            json={"phone_number": e164, "text": msg},
            timeout=30.0,
        )
        if resp.status_code == 200 and resp.json().get("success"):
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
    score_color = "#16a34a" if (score or 0) >= 80 else ("#d97706" if (score or 0) >= 60 else "#dc2626")

    # Build findings rows for the email table
    rows = ""
    sev_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
    for f in findings:
        emoji = sev_emoji.get(f.get("severity", "info"), "•")
        import html as _html
        rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:12px 14px;font-size:14px;color:#111827;">{emoji} {_html.escape(f.get("message",""))}</td>
          <td style="padding:12px 14px;font-size:13px;color:#374151;">{_html.escape(f.get("solution",""))}</td>
        </tr>"""

    demo_block = ""
    if demo_url:
        demo_block = f"""
      <div style="background:linear-gradient(135deg,#1e3a8a,#2563eb);border-radius:14px;padding:28px 24px;text-align:center;margin:28px 0;">
        <p style="color:rgba(255,255,255,.85);font-size:13px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.8px;">✨ Surprise — it's already done!</p>
        <p style="color:#fff;font-size:18px;font-weight:800;margin:0 0 18px;line-height:1.3;">
          We built a free demo of <br/>{business_name}'s new site
        </p>
        <a href="{demo_url}" style="display:inline-block;background:#f97316;color:#fff;font-weight:800;padding:14px 32px;border-radius:10px;text-decoration:none;font-size:15px;letter-spacing:.3px;">
          See your new site →
        </a>
        <p style="color:rgba(255,255,255,.65);font-size:12px;margin:14px 0 0;">No commitment. Totally free. Just showing you what's possible 💙</p>
      </div>"""

    findings_section = ""
    if findings:
        findings_section = f"""
    <h2 style="font-size:15px;font-weight:700;color:#111827;margin:28px 0 12px;">Here's what we found 🔍</h2>
    <p style="font-size:14px;color:#6b7280;margin:0 0 16px;">Don't worry — these are all fixable! Here's a quick summary:</p>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:.5px;font-weight:600;">What we noticed</th>
          <th style="padding:10px 14px;text-align:left;font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:.5px;font-weight:600;">The easy fix</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""
    else:
        findings_section = "<p style='color:#16a34a;font-weight:700;font-size:15px;'>✅ Great news — this site passes all SEO checks!</p>"

    html_body = f"""
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f3f4f6;padding:0;margin:0;">
<div style="max-width:600px;margin:40px auto 24px;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#0f172a,#1e3a8a);padding:32px 36px 28px;">
    <p style="font-size:12px;color:rgba(255,255,255,.55);margin:0 0 6px;text-transform:uppercase;letter-spacing:1px;">A little gift from Equestro Labs 🎁</p>
    <h1 style="font-size:24px;font-weight:800;color:#fff;margin:0 0 8px;line-height:1.2;">{business_name} — Free SEO Report</h1>
    <div style="display:inline-block;background:rgba(255,255,255,.1);border-radius:999px;padding:6px 16px;margin-top:4px;">
      <span style="color:#fff;font-size:14px;font-weight:700;">Score: <span style="color:{score_color};">{score_str}</span></span>
      <span style="color:rgba(255,255,255,.5);font-size:13px;"> · {len(findings)} thing{"s" if len(findings) != 1 else ""} to improve</span>
    </div>
  </div>

  <div style="padding:32px 36px;">

    <!-- Personal intro -->
    <p style="color:#374151;font-size:16px;line-height:1.7;margin:0 0 6px;">
      Hi there! 👋 I'm <strong style="color:#111827;">Natalie</strong> from Equestro Labs.
    </p>
    <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 24px;">
      I came across <strong style="color:#111827;">{business_name}</strong> and loved what you're doing — so I went ahead and ran a completely free website audit, just to see where things stand. The good news? There are only a handful of things holding the site back, and they're all totally fixable. 🙌
    </p>

    {demo_block}

    <!-- Report link pill -->
    <div style="background:#eff6ff;border:1.5px solid #bfdbfe;border-radius:12px;padding:18px 22px;margin-bottom:28px;text-align:center;">
      <p style="font-size:14px;color:#1e40af;font-weight:700;margin:0 0 6px;">📊 Your full interactive report</p>
      <p style="font-size:13px;color:#6b7280;margin:0 0 10px;">Click the link below — it's yours, forever, completely free.</p>
      <a href="{report_url}" style="color:#2563eb;font-size:14px;font-weight:600;word-break:break-all;">{report_url}</a>
    </div>

    {findings_section}

    <!-- CTA -->
    <div style="margin-top:32px;padding:28px 24px;background:#f0fdf4;border-radius:14px;text-align:center;">
      <p style="font-size:16px;font-weight:700;color:#111827;margin:0 0 8px;">Want us to fix this for you? 🚀</p>
      <p style="color:#374151;font-size:14px;line-height:1.6;margin:0 0 20px;">
        I'd love to walk you through everything — no jargon, no pressure, no catch. Just a quick friendly chat about what we can do for {business_name}.
      </p>
      <a href="mailto:natalie@equestrolabs.com?subject=Re: {business_name} website" style="display:inline-block;background:#1e40af;color:#fff;font-weight:700;padding:13px 26px;border-radius:10px;text-decoration:none;font-size:14px;margin:0 6px 8px;">
        💌 Reply to this email
      </a>
      <a href="sms:{NATALIE_PHONE}" style="display:inline-block;background:#16a34a;color:#fff;font-weight:700;padding:13px 26px;border-radius:10px;text-decoration:none;font-size:14px;margin:0 6px 8px;">
        💬 Text me directly
      </a>
    </div>
  </div>

  <!-- Footer -->
  <div style="background:#f9fafb;padding:18px 36px;border-top:1px solid #f3f4f6;">
    <p style="color:#9ca3af;font-size:12px;margin:0;text-align:center;line-height:1.7;">
      Sent with love by Natalie · Equestro Labs<br/>
      natalie@equestrolabs.com · {NATALIE_PHONE}<br/>
      <a href="{report_url}" style="color:#9ca3af;text-decoration:underline;">View your report anytime</a>
    </p>
  </div>
</div>
</body></html>"""

    text_body = (
        f"Hi! 😊 I'm Natalie from Equestro Labs — I hope this finds you well!\n\n"
        f"I came across {business_name} and loved what you're doing, so I went ahead and ran a "
        f"free SEO audit on your website. Here's a quick summary:\n\n"
        f"  Score: {score_str}\n"
        f"  Issues found: {len(findings)}\n\n"
        f"The great news? Every single issue is fixable — and I also went ahead and built a free "
        f"demo showing what {business_name}'s site could look like all polished up. No strings "
        f"attached, I just wanted to show you what's possible!\n\n"
        f"  Your full report (free, forever): {report_url}\n"
        f"  Your free demo site: {demo_url}\n\n"
        f"I'd love to chat whenever you're ready — even just a quick text. "
        f"No pressure at all, just here to help!\n\n"
        f"Warmly,\nNatalie\nEquestro Labs\n"
        f"natalie@equestrolabs.com · {NATALIE_PHONE}"
    )

    subject = f"I built something free for {business_name} 🎁"

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
