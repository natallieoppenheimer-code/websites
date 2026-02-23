"""
Render a shareable HTML audit report page from a stored report dict.
"""
import html as _html

_SEVERITY_COLOR = {"critical": "#dc2626", "warning": "#d97706", "info": "#2563eb"}
_SEVERITY_LABEL = {"critical": "Critical", "warning": "Warning", "info": "Info"}
_SEVERITY_BG    = {"critical": "#fef2f2", "warning": "#fffbeb", "info": "#eff6ff"}

def _e(text: str) -> str:
    """HTML-escape a string so tags in content are shown literally."""
    return _html.escape(str(text) if text else "")


def render_report_html(report: dict, render_base_url: str = "https://websites-pilv.onrender.com") -> str:
    business_name = report.get("business_name", "Your Business")
    audited_url   = report.get("audited_url", report.get("url", ""))
    demo_url      = report.get("demo_url", "")
    score         = report.get("summary_score")
    findings      = report.get("findings", [])
    slug          = report.get("slug", "")
    biz_safe      = _e(business_name)   # HTML-safe business name

    score_display = f"{score:.0f}" if score is not None else "—"
    score_color   = "#16a34a" if (score or 0) >= 80 else "#d97706" if (score or 0) >= 60 else "#dc2626"

    # Build finding cards — escape ALL user-derived text so <tags> show literally
    finding_cards = ""
    for f in findings:
        sev   = f.get("severity", "info")
        color = _SEVERITY_COLOR.get(sev, "#2563eb")
        bg    = _SEVERITY_BG.get(sev, "#eff6ff")
        label = _SEVERITY_LABEL.get(sev, sev.title())
        finding_cards += f"""
      <div style="border-left:4px solid {color};background:{bg};padding:16px 20px;border-radius:10px;margin-bottom:14px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;">
          <span style="background:{color};color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:99px;text-transform:uppercase;letter-spacing:.5px;">{label}</span>
          <span style="font-size:12px;color:#6b7280;text-transform:capitalize;">{_e(f.get("category",""))}</span>
        </div>
        <p style="font-weight:600;color:#111827;margin:0 0 6px;font-size:15px;line-height:1.4;">{_e(f.get("message",""))}</p>
        <p style="font-size:13px;color:#374151;margin:0;line-height:1.5;word-break:break-word;">
          <strong style="color:#111;">Fix:</strong> {_e(f.get("solution",""))}
        </p>
      </div>"""

    no_findings_html = ""
    if not findings:
        no_findings_html = """
      <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:12px;padding:24px;text-align:center;color:#166534;">
        <div style="font-size:40px;margin-bottom:8px;">🎉</div>
        <strong>No issues found — this site passes all checks!</strong>
      </div>"""

    demo_section = ""
    if demo_url:
        demo_section = f"""
    <div style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8);color:#fff;border-radius:16px;padding:32px;text-align:center;margin-top:32px;">
      <h2 style="margin:0 0 8px;font-size:22px;">See What Your Site Could Look Like</h2>
      <p style="opacity:.85;margin:0 0 20px;font-size:15px;">
        We rebuilt <strong>{business_name}</strong> with proper SEO and a modern design — for free, just to show you the possibilities.
      </p>
      <a href="{demo_url}" target="_blank"
         style="display:inline-block;background:#f97316;color:#fff;font-weight:700;padding:14px 32px;border-radius:12px;text-decoration:none;font-size:16px;">
        👀 View Your Rebuilt Demo Site →
      </a>
      <p style="margin:16px 0 0;font-size:12px;opacity:.6;">No cost, no commitment — just a preview of what's possible.</p>
    </div>"""

    cta_section = f"""
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:16px;padding:32px;text-align:center;margin-top:24px;">
      <h2 style="margin:0 0 8px;color:#111827;font-size:20px;">Ready to Fix These Issues?</h2>
      <p style="color:#6b7280;margin:0 0 20px;font-size:15px;">
        Natalie from Equestro Labs will walk you through every fix and rebuild your site with proper SEO — usually in under a week.
      </p>
      <a href="mailto:natalie@equestrolabs.com?subject=Website audit for {business_name}&body=Hi Natalie, I saw my audit report and I'd like to discuss fixing my site."
         style="display:inline-block;background:#1e40af;color:#fff;font-weight:700;padding:14px 32px;border-radius:12px;text-decoration:none;font-size:15px;">
        📧 Email Natalie
      </a>
      &nbsp;&nbsp;
      <a href="sms:+16692587531"
         style="display:inline-block;background:#16a34a;color:#fff;font-weight:700;padding:14px 32px;border-radius:12px;text-decoration:none;font-size:15px;">
        💬 Text Natalie
      </a>
    </div>"""

    audit_url_display = audited_url[:60] + "…" if len(audited_url) > 60 else audited_url

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
    <title>Website Audit Report — {biz_safe}</title>
  <meta name="description" content="Free SEO audit report for {biz_safe}. Score: {score_display}/100 with {len(findings)} findings."/>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f3f4f6;color:#111827;}}
    .container{{max-width:720px;margin:0 auto;padding:24px 16px 48px;}}
    .card{{background:#fff;border-radius:16px;padding:28px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.08);}}
    a{{color:#1d4ed8;}}
  </style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="card" style="text-align:center;background:linear-gradient(135deg,#1e3a8a,#1d4ed8);color:#fff;">
    <p style="font-size:12px;opacity:.7;margin-bottom:4px;text-transform:uppercase;letter-spacing:1px;">Free SEO Audit Report</p>
    <h1 style="font-size:26px;font-weight:800;margin-bottom:4px;">{biz_safe}</h1>
    <p style="opacity:.8;font-size:13px;margin-bottom:20px;">
      Audited: <a href="{audited_url}" target="_blank" style="color:#fbbf24;">{audit_url_display}</a>
    </p>
    <div style="display:inline-flex;align-items:center;justify-content:center;background:rgba(255,255,255,.15);border-radius:16px;padding:16px 32px;gap:20px;">
      <div>
        <div style="font-size:52px;font-weight:900;color:{score_color if score_color != '#16a34a' else '#86efac'};">{score_display}</div>
        <div style="font-size:13px;opacity:.75;">out of 100</div>
      </div>
      <div style="text-align:left;">
        <div style="font-size:22px;font-weight:700;">{len(findings)} issue{"s" if len(findings) != 1 else ""} found</div>
        <div style="font-size:13px;opacity:.75;">affecting SEO & visibility</div>
      </div>
    </div>
  </div>

  <!-- Findings -->
  <div class="card">
    <h2 style="font-size:18px;font-weight:700;margin-bottom:16px;color:#111827;">
      {"Issues Found" if findings else "All Checks Passed"}
    </h2>
    {finding_cards}
    {no_findings_html}
  </div>

  {demo_section}
  {cta_section}

  <!-- Footer -->
  <p style="text-align:center;color:#9ca3af;font-size:12px;margin-top:24px;">
    Report generated by <a href="{render_base_url}/audit/dashboard">Equestro Labs Website Audit Tool</a> ·
    <a href="mailto:natalie@equestrolabs.com">natalie@equestrolabs.com</a>
  </p>

</div>
</body>
</html>"""
