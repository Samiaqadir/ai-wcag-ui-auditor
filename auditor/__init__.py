"""
AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor Package.
Day-3 Complete Streamlit QA Dashboard, Triage Engine, and Multi-Format Exporter.
"""

from auditor.models import (
    Violation,
    Severity,
    TriageStatus,
    PageAuditResult,
    AuditSummaryReport,
    BoundingBox,
    LayoutShift,
    StyleRegression,
    StructuralDiff,
    RegressionDiffReport,
)
from auditor.contrast import calculate_contrast_ratio, calculate_luminance, parse_color, is_contrast_compliant
from auditor.parser import PlaywrightDOMInspector, PageInspectionResult, generate_css_selector
from auditor.rules import audit_page_file
from auditor.llm_remediator import LLMRemediator
from auditor.regression import compare_page_snapshots
from auditor.exporter import export_to_html, export_to_markdown, export_to_csv

__all__ = [
    "Violation",
    "Severity",
    "TriageStatus",
    "PageAuditResult",
    "AuditSummaryReport",
    "BoundingBox",
    "LayoutShift",
    "StyleRegression",
    "StructuralDiff",
    "RegressionDiffReport",
    "calculate_contrast_ratio",
    "calculate_luminance",
    "parse_color",
    "is_contrast_compliant",
    "PlaywrightDOMInspector",
    "PageInspectionResult",
    "generate_css_selector",
    "audit_page_file",
    "LLMRemediator",
    "compare_page_snapshots",
    "export_to_html",
    "export_to_markdown",
    "export_to_csv",
]
