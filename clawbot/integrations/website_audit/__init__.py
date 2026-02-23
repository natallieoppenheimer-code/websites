"""Website/SEO audit: uncover badly run sites and poor SEO; return insights and solutions."""
from clawbot.integrations.website_audit.auditor import run_audit, AuditReport, report_to_dict

__all__ = ["run_audit", "AuditReport", "report_to_dict"]
