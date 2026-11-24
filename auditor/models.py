"""
Data models and structured schemas for WCAG accessibility violations,
remediations, and visual/DOM regression diff reports.
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
    """Structured WCAG Accessibility Violation Schema with Context-Aware Remediation."""
    rule_id: str = Field(..., description="Unique WCAG rule identifier, e.g. 'WCAG-1.1.1'")
    rule_name: str = Field(..., description="Human-readable rule name")
    severity: Severity = Field(..., description="Severity classification: Critical, Serious, Moderate, or Minor")
    dom_selector: str = Field(..., description="Specific CSS selector path identifying the violating element")
    raw_html_snippet: str = Field(..., description="Raw HTML snippet of the element exhibiting the violation")
    issue_explanation: str = Field(..., description="Detailed explanation of the WCAG barrier and impact")
    suggested_fix: str = Field(..., description="Actionable remediation instructions")
    before_html: str = Field(default="", description="Original HTML snippet before remediation")
    after_html: str = Field(default="", description="Drop-in remediated HTML/ARIA code patch")


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
    engine_version: str = "2.0.0-day2"
    total_pages_scanned: int
    passed_pages: int
    failed_pages: int
    total_violations: int
    violations_by_severity: Dict[str, int]
    results: List[PageAuditResult]


# =========================================================================
# Visual Layout & DOM Regression Diff Models
# =========================================================================

class BoundingBox(BaseModel):
    """Element 2D geometry bounding box."""
    x: float
    y: float
    width: float
    height: float


class LayoutShift(BaseModel):
    """Detected geometric shift or resize between baseline and modified snapshots."""
    dom_selector: str
    baseline_box: BoundingBox
    modified_box: BoundingBox
    delta_x: float
    delta_y: float
    delta_width: float
    delta_height: float
    shift_description: str


class StyleRegression(BaseModel):
    """Detected CSS computed style alteration."""
    dom_selector: str
    property_name: str
    baseline_value: str
    modified_value: str
    impact: str


class StructuralDiff(BaseModel):
    """DOM node additions and removals."""
    added_elements: List[str] = Field(default_factory=list)
    removed_elements: List[str] = Field(default_factory=list)


class RegressionDiffReport(BaseModel):
    """Aggregated visual layout and DOM regression diff report."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    baseline_page: str
    modified_page: str
    total_layout_shifts: int
    total_style_regressions: int
    total_structural_changes: int
    layout_shifts: List[LayoutShift]
    style_regressions: List[StyleRegression]
    structural_changes: StructuralDiff
    summary: str
