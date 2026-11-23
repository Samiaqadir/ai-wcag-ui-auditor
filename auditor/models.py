"""
Data models and structured schemas for WCAG accessibility violations and audit reports.
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """WCAG Violation Severity Levels."""
    CRITICAL = "Critical"
    SERIOUS = "Serious"
    MODERATE = "Moderate"
    MINOR = "Minor"


class Violation(BaseModel):
    """Structured WCAG Accessibility Violation Schema."""
    rule_id: str = Field(..., description="Unique WCAG rule identifier, e.g. 'WCAG-1.1.1'")
    rule_name: str = Field(..., description="Human-readable rule name")
    severity: Severity = Field(..., description="Severity classification: Critical, Serious, Moderate, or Minor")
    dom_selector: str = Field(..., description="Specific CSS selector path identifying the violating element")
    raw_html_snippet: str = Field(..., description="Raw HTML snippet of the element exhibiting the violation")
    issue_explanation: str = Field(..., description="Detailed explanation of the WCAG barrier and impact")
    suggested_fix: str = Field(..., description="Actionable remediation code or instructions to resolve the violation")


class PageAuditResult(BaseModel):
    """Complete audit results for an individual HTML document or page."""
    page_name: str
    file_path: str
    total_violations: int
    violations_by_severity: Dict[str, int]
    violations: List[Violation]
    status: str = Field(..., description="'PASSED' if 0 violations, else 'FAILED'")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditSummaryReport(BaseModel):
    """Aggregated multi-page audit summary report."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    engine_version: str = "1.0.0-day1"
    total_pages_scanned: int
    passed_pages: int
    failed_pages: int
    total_violations: int
    violations_by_severity: Dict[str, int]
    results: List[PageAuditResult]
