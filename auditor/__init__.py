"""
AI Accessibility (WCAG) & UI Regression Auditor Package.
"""

from auditor.models import Violation, Severity, PageAuditResult, AuditSummaryReport
from auditor.contrast import calculate_contrast_ratio, calculate_luminance, parse_color
from auditor.rules import audit_html_content, audit_page_file

__all__ = [
    "Violation",
    "Severity",
    "PageAuditResult",
    "AuditSummaryReport",
    "calculate_contrast_ratio",
    "calculate_luminance",
    "parse_color",
    "audit_html_content",
    "audit_page_file",
]
