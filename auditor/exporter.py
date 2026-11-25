"""
Multi-Format Report Exporter for AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor.
Generates:
1. Self-contained, styled, print-ready HTML executive QA reports
2. GitHub/Jira-ready Markdown summaries with severity tables and code diffs
3. Flat structured CSV reports for Jira / Excel import
Includes dynamic WCAG Compliance Score calculations excluding False Positives.
"""

import csv
import io
import html
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timezone

from auditor.models import Violation, Severity, PageAuditResult, RegressionDiffReport


def get_violation_key(v: Violation, idx: int = 0) -> str:
    """Returns a deterministic unique key for a violation."""
    return f"{v.rule_id}::{v.dom_selector}"


def calculate_wcag_score(
    violations: List[Violation],
    triage_data: Optional[Dict[str, Dict[str, Any]]] = None,
) -> float:
    """
    Dynamically calculates the WCAG 2.1 AA Compliance Score out of 100%.
    CRITICAL: Automatically excludes items marked as 'False Positive' during triage!

    Severity Weight Deductions for Active Findings (Pending or Confirmed Defect):
    - Critical: -15 points (Complete assistive technology blocker)
    - Serious:  -8 points (Significant difficulty or navigation barrier)
    - Moderate: -4 points (Compliance failure with partial workaround)
    - Minor:    -1 point  (Usability or semantic imperfection)
    """
    if not violations:
        return 100.0

    penalties = {
        Severity.CRITICAL.value: 15,
        Severity.SERIOUS.value: 8,
        Severity.MODERATE.value: 4,
        Severity.MINOR.value: 1,
    }

    active_penalty = 0
    for idx, v in enumerate(violations):
        key = get_violation_key(v, idx)
        status = "Pending"
        if triage_data and key in triage_data:
            status = triage_data[key].get("status", "Pending")
        elif hasattr(v, "triage_status"):
            status = getattr(v, "triage_status", "Pending")

        # Exclude False Positives from compliance penalty calculation!
        if status == "False Positive":
            continue

        sev = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
        active_penalty += penalties.get(sev, 4)

    score = max(0.0, min(100.0, 100.0 - active_penalty))
    return round(score, 1)


def get_compliance_grade(score: float) -> Dict[str, str]:
    """Returns human-readable grade and badge style for a given compliance score."""
    if score >= 90:
        return {"grade": "Grade A", "label": "Compliant", "color": "#10b981", "bg": "#ecfdf5"}
    elif score >= 75:
        return {"grade": "Grade B", "label": "Needs Improvement", "color": "#f59e0b", "bg": "#fffbeb"}
    elif score >= 50:
        return {"grade": "Grade C", "label": "Substantial Barriers", "color": "#f97316", "bg": "#fff7ed"}
    else:
        return {"grade": "Grade F", "label": "Non-Compliant", "color": "#ef4444", "bg": "#fef2f2"}


def export_to_html(
    audit_result: Union[PageAuditResult, List[Violation]],
    triage_data: Optional[Dict[str, Dict[str, Any]]] = None,
    page_name: str = "Target Page",
    regression_report: Optional[RegressionDiffReport] = None,
) -> str:
    """
    Exports audited and triaged results into a self-contained, beautifully styled,
    print-ready executive QA audit report.
    """
    if isinstance(audit_result, PageAuditResult):
        violations = audit_result.violations
        doc_name = audit_result.page_name or page_name
    else:
        violations = audit_result
        doc_name = page_name

    triage_data = triage_data or {}
    score = calculate_wcag_score(violations, triage_data)
    grade_info = get_compliance_grade(score)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Counts
    total_findings = len(violations)
    confirmed_defects = 0
    false_positives = 0
    wont_fix_count = 0
    pending_count = 0
    crit_serious_count = 0

    for idx, v in enumerate(violations):
        key = get_violation_key(v, idx)
        status = triage_data.get(key, {}).get("status", "Pending")
        if status == "Confirmed Defect":
            confirmed_defects += 1
        elif status == "False Positive":
            false_positives += 1
        elif status == "Won't Fix":
            wont_fix_count += 1
        else:
            pending_count += 1

        sev = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
        if sev in [Severity.CRITICAL.value, Severity.SERIOUS.value] and status != "False Positive":
            crit_serious_count += 1

    # Severity badge colors
    sev_colors = {
        "Critical": ("#fee2e2", "#991b1b", "#ef4444"),
        "Serious": ("#ffedd5", "#9a3412", "#f97316"),
        "Moderate": ("#fef3c7", "#92400e", "#f59e0b"),
        "Minor": ("#e0f2fe", "#075985", "#0ea5e9"),
    }

    # Triage badge colors
    triage_colors = {
        "Confirmed Defect": ("#fee2e2", "#991b1b", "#dc2626"),
        "False Positive": ("#d1fae5", "#065f46", "#10b981"),
        "Won't Fix": ("#f3f4f6", "#374151", "#6b7280"),
        "Pending": ("#fef9c3", "#854d0e", "#ca8a04"),
    }

    # Build issues HTML
    issues_html = []
    for idx, v in enumerate(violations, 1):
        key = get_violation_key(v, idx - 1)
        t_info = triage_data.get(key, {})
        status = t_info.get("status", "Pending")
        notes = t_info.get("notes", "").strip()

        sev_str = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
        s_bg, s_fg, s_bd = sev_colors.get(sev_str, ("#f3f4f6", "#374151", "#9ca3af"))
        t_bg, t_fg, t_bd = triage_colors.get(status, ("#f3f4f6", "#374151", "#9ca3af"))

        before_code = v.before_html or v.raw_html_snippet or "<!-- Missing snippet -->"
        after_code = v.after_html or v.suggested_fix or "<!-- Remediation pending -->"

        notes_section = ""
        if notes:
            notes_section = f"""
            <div class="reviewer-notes-box">
                <span class="reviewer-label">💬 Reviewer QA Triage Note:</span>
                <span class="reviewer-text">{html.escape(notes)}</span>
            </div>
            """

        issues_html.append(f"""
        <div class="issue-card" id="issue-{idx}">
            <div class="issue-card-header">
                <div class="issue-title-group">
                    <span class="issue-index">#{idx}</span>
                    <span class="rule-id">{html.escape(v.rule_id)}</span>
                    <h3 class="rule-name">{html.escape(v.rule_name)}</h3>
                </div>
                <div class="badge-group">
                    <span class="badge badge-sev" style="background:{s_bg}; color:{s_fg}; border-color:{s_bd};">
                        {html.escape(sev_str)}
                    </span>
                    <span class="badge badge-triage" style="background:{t_bg}; color:{t_fg}; border-color:{t_bd};">
                        ● {html.escape(status)}
                    </span>
                </div>
            </div>

            <div class="issue-meta">
                <div class="meta-item">
                    <span class="meta-label">Target DOM Selector:</span>
                    <code class="meta-selector">{html.escape(v.dom_selector)}</code>
                </div>
            </div>

            <div class="issue-body">
                <p class="issue-explanation"><strong>Accessibility Barrier:</strong> {html.escape(v.issue_explanation)}</p>
                <p class="issue-fix"><strong>Remediation Strategy:</strong> {html.escape(v.suggested_fix)}</p>
            </div>

            {notes_section}

            <div class="code-diff-container">
                <div class="code-pane before-pane">
                    <div class="pane-header">
                        <span class="pane-indicator red-dot"></span>
                        <span class="pane-title">🔴 Original Non-Compliant HTML</span>
                    </div>
                    <pre><code>{html.escape(before_code)}</code></pre>
                </div>
                <div class="code-pane after-pane">
                    <div class="pane-header">
                        <span class="pane-indicator green-dot"></span>
                        <span class="pane-title">🟢 Recommended Accessible Patch</span>
                    </div>
                    <pre><code>{html.escape(after_code)}</code></pre>
                </div>
            </div>
        </div>
        """)

    all_issues_rendered = "\n".join(issues_html) if issues_html else "<p class='no-issues'>🎉 Zero WCAG violations detected. Document is fully compliant!</p>"

    # Optional regression diff section
    regression_section = ""
    if regression_report:
        regression_section = f"""
        <div class="regression-section">
            <h2 class="section-title">📐 Visual Layout & DOM Regression Diff Summary</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-title">Layout Shifts</div>
                    <div class="kpi-value">{regression_report.total_layout_shifts}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Style Mutations</div>
                    <div class="kpi-value">{regression_report.total_style_regressions}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">DOM Elements Added</div>
                    <div class="kpi-value">{len(regression_report.structural_changes.added_elements)}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">DOM Elements Removed</div>
                    <div class="kpi-value">{len(regression_report.structural_changes.removed_elements)}</div>
                </div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WCAG 2.1 AA Executive QA Audit Report - {html.escape(doc_name)}</title>
    <style>
        :root {{
            --bg-canvas: #0f172a;
            --bg-card: #1e293b;
            --bg-card-subtle: #182234;
            --border-card: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-faint: #64748b;
            --accent-primary: #3b82f6;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        @media print {{
            body {{ background: #ffffff !important; color: #0f172a !important; }}
            .issue-card {{ break-inside: avoid; border: 1px solid #cbd5e1 !important; background: #ffffff !important; color: #0f172a !important; }}
            .code-pane {{ background: #f8fafc !important; color: #0f172a !important; }}
            .no-print {{ display: none !important; }}
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-canvas);
            color: var(--text-main);
            font-family: var(--font-family);
            line-height: 1.6;
            padding: 32px 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        /* Header */
        .report-header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--border-card);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }}
        .header-left h1 {{
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 6px;
            letter-spacing: -0.5px;
        }}
        .header-meta {{
            font-size: 13px;
            color: var(--text-muted);
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .header-meta span strong {{
            color: #e2e8f0;
        }}
        .score-box {{
            background: rgba(15, 23, 42, 0.8);
            border: 2px solid {grade_info['color']};
            border-radius: 14px;
            padding: 16px 24px;
            text-align: center;
            min-width: 170px;
        }}
        .score-val {{
            font-size: 38px;
            font-weight: 900;
            color: {grade_info['color']};
            line-height: 1;
        }}
        .score-label {{
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .score-grade {{
            display: inline-block;
            margin-top: 6px;
            padding: 2px 10px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
            background: {grade_info['color']};
            color: #ffffff;
        }}
        /* KPI Cards */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .kpi-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }}
        .kpi-title {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }}
        .kpi-value {{
            font-size: 30px;
            font-weight: 800;
            color: #ffffff;
        }}
        .kpi-subtext {{
            font-size: 12px;
            color: var(--text-faint);
            margin-top: 4px;
        }}
        /* Section Title */
        .section-title {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 16px;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        /* Issue Card */
        .issue-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            transition: transform 0.15s ease;
        }}
        .issue-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 14px;
            padding-bottom: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .issue-title-group {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .issue-index {{
            font-size: 13px;
            font-weight: 700;
            color: var(--text-faint);
        }}
        .rule-id {{
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 12px;
            font-weight: 700;
            font-family: var(--font-mono);
        }}
        .rule-name {{
            font-size: 17px;
            font-weight: 700;
            color: #ffffff;
        }}
        .badge-group {{
            display: flex;
            gap: 8px;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: 1px solid transparent;
        }}
        .issue-meta {{
            margin-bottom: 14px;
            font-size: 13px;
        }}
        .meta-label {{
            color: var(--text-muted);
            font-weight: 600;
            margin-right: 6px;
        }}
        .meta-selector {{
            font-family: var(--font-mono);
            background: #0f172a;
            border: 1px solid #334155;
            padding: 3px 8px;
            border-radius: 6px;
            color: #38bdf8;
            font-size: 12px;
            word-break: break-all;
        }}
        .issue-body {{
            font-size: 14px;
            color: #cbd5e1;
            margin-bottom: 16px;
        }}
        .issue-explanation {{
            margin-bottom: 8px;
        }}
        .issue-fix {{
            color: #94a3b8;
        }}
        /* Reviewer QA Note */
        .reviewer-notes-box {{
            background: rgba(234, 179, 8, 0.1);
            border-left: 4px solid #eab308;
            border-radius: 0 8px 8px 0;
            padding: 10px 16px;
            margin-bottom: 16px;
            font-size: 13px;
            color: #fef08a;
        }}
        .reviewer-label {{
            font-weight: 700;
            margin-right: 6px;
        }}
        /* Code Diff Viewer */
        .code-diff-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 14px;
        }}
        @media (max-width: 800px) {{
            .code-diff-container {{ grid-template-columns: 1fr; }}
        }}
        .code-pane {{
            background: #090d16;
            border: 1px solid #1e293b;
            border-radius: 8px;
            overflow: hidden;
        }}
        .pane-header {{
            background: #111827;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid #1f2937;
        }}
        .before-pane .pane-title {{ color: #f87171; }}
        .after-pane .pane-title {{ color: #4ade80; }}
        .code-pane pre {{
            margin: 0;
            padding: 14px;
            overflow-x: auto;
            font-family: var(--font-mono);
            font-size: 12px;
            line-height: 1.5;
            color: #e2e8f0;
        }}
        .footer {{
            margin-top: 48px;
            text-align: center;
            font-size: 12px;
            color: var(--text-faint);
            border-top: 1px solid var(--border-card);
            padding-top: 24px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="report-header">
            <div class="header-left">
                <h1>🛡️ WCAG 2.1 AA Executive QA Accessibility Report</h1>
                <div class="header-meta">
                    <span><strong>Audited Target:</strong> {html.escape(doc_name)}</span>
                    <span><strong>Generated:</strong> {html.escape(timestamp)}</span>
                    <span><strong>Standard:</strong> WCAG 2.1 Level AA</span>
                    <span><strong>Auditor Suite:</strong> Day-3 Streamlit QA Edition</span>
                </div>
            </div>
            <div class="score-box">
                <div class="score-val">{score}%</div>
                <div class="score-label">WCAG Compliance Score</div>
                <div class="score-grade">{grade_info['grade']} ({grade_info['label']})</div>
            </div>
        </header>

        <!-- KPI Grid -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Total Detected Findings</div>
                <div class="kpi-value">{total_findings}</div>
                <div class="kpi-subtext">Automated 10-rule inspection</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Confirmed QA Defects</div>
                <div class="kpi-value" style="color: #ef4444;">{confirmed_defects}</div>
                <div class="kpi-subtext">Triaged & verified as real barriers</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Critical & Serious Blockers</div>
                <div class="kpi-value" style="color: #f97316;">{crit_serious_count}</div>
                <div class="kpi-subtext">Active screen-reader blockers</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">False Positives Filtered</div>
                <div class="kpi-value" style="color: #10b981;">{false_positives}</div>
                <div class="kpi-subtext">Excluded from compliance deduction</div>
            </div>
        </div>

        {regression_section}

        <!-- Issues List -->
        <section>
            <h2 class="section-title">🔍 Detailed Accessibility Findings & Remediated Patches</h2>
            {all_issues_rendered}
        </section>

        <!-- Footer -->
        <footer class="footer">
            <p>AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor • Day-3 Executive QA Report</p>
            <p>Produced automatically with context-aware LLM remediation and interactive QA human triage.</p>
        </footer>
    </div>
</body>
</html>
"""
    return html_content


def export_to_markdown(
    audit_result: Union[PageAuditResult, List[Violation]],
    triage_data: Optional[Dict[str, Dict[str, Any]]] = None,
    page_name: str = "Target Page",
) -> str:
    """
    Exports audited and triaged results into clean GitHub/Jira-ready Markdown summary
    with severity tables, triage status, reviewer notes, and fenced HTML diff blocks.
    """
    if isinstance(audit_result, PageAuditResult):
        violations = audit_result.violations
        doc_name = audit_result.page_name or page_name
    else:
        violations = audit_result
        doc_name = page_name

    triage_data = triage_data or {}
    score = calculate_wcag_score(violations, triage_data)
    grade = get_compliance_grade(score)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Counts
    total_findings = len(violations)
    confirmed_defects = sum(1 for idx, v in enumerate(violations) if triage_data.get(get_violation_key(v, idx), {}).get("status") == "Confirmed Defect")
    false_positives = sum(1 for idx, v in enumerate(violations) if triage_data.get(get_violation_key(v, idx), {}).get("status") == "False Positive")
    wont_fix = sum(1 for idx, v in enumerate(violations) if triage_data.get(get_violation_key(v, idx), {}).get("status") == "Won't Fix")
    pending = total_findings - confirmed_defects - false_positives - wont_fix

    lines = [
        f"# WCAG 2.1 AA Executive QA Accessibility & Remediation Report",
        "",
        f"**Target Document:** `{doc_name}`  ",
        f"**Audit Timestamp:** `{timestamp}`  ",
        f"**Compliance Score:** **{score}%** ({grade['grade']} - {grade['label']})  ",
        f"**Standard:** WCAG 2.1 Level AA  ",
        f"**Engine:** Day-3 Streamlit QA Auditor Suite  ",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "| Metric | Count / Status | Details |",
        "| :--- | :--- | :--- |",
        f"| **WCAG Compliance Score** | **{score}%** | {grade['grade']} ({grade['label']}) |",
        f"| **Total Violations Detected** | {total_findings} | Full 10-rule inspection suite |",
        f"| **Confirmed QA Defects** | {confirmed_defects} | Verified action items for engineering |",
        f"| **False Positives Filtered** | {false_positives} | Dynamically excluded from penalty |",
        f"| **Won't Fix / Accepted Risk** | {wont_fix} | Documented non-blocker items |",
        f"| **Pending Review** | {pending} | Awaiting QA triage confirmation |",
        "",
        "---",
        "",
        "## Detailed Triaged Findings & Accessible Code Patches",
        "",
    ]

    for idx, v in enumerate(violations, 1):
        key = get_violation_key(v, idx - 1)
        t_info = triage_data.get(key, {})
        status = t_info.get("status", "Pending")
        notes = t_info.get("notes", "").strip()
        sev_str = v.severity.value if hasattr(v.severity, "value") else str(v.severity)

        before_code = v.before_html or v.raw_html_snippet or "<!-- Missing snippet -->"
        after_code = v.after_html or v.suggested_fix or "<!-- Remediation pending -->"

        lines.append(f"### {idx}. {v.rule_name} (`{v.rule_id}`)")
        lines.append(f"- **Severity:** `{sev_str}`")
        lines.append(f"- **QA Triage Status:** `{status}`")
        if notes:
            lines.append(f"- **QA Reviewer Note:** *\"{notes}\"*")
        lines.append(f"- **Target DOM Selector:** `{v.dom_selector}`")
        lines.append(f"- **Issue Explanation:** {v.issue_explanation}")
        lines.append(f"- **Remediation Strategy:** {v.suggested_fix}")
        lines.append("")
        lines.append("#### 🔴 Original Non-Compliant HTML")
        lines.append("```html")
        lines.append(before_code)
        lines.append("```")
        lines.append("")
        lines.append("#### 🟢 Recommended Accessible Patch")
        lines.append("```html")
        lines.append(after_code)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def export_to_csv(
    audit_result: Union[PageAuditResult, List[Violation]],
    triage_data: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """
    Exports audited and triaged results into a clean, flat structured CSV string
    ready for direct Jira, GitHub Issues, or Excel import.
    """
    if isinstance(audit_result, PageAuditResult):
        violations = audit_result.violations
    else:
        violations = audit_result

    triage_data = triage_data or {}
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Headers
    headers = [
        "Rule ID",
        "Rule Name",
        "Severity",
        "Triage Status",
        "Reviewer Notes",
        "DOM Selector",
        "Issue Explanation",
        "Before HTML",
        "After HTML",
    ]
    writer.writerow(headers)

    for idx, v in enumerate(violations):
        key = get_violation_key(v, idx)
        t_info = triage_data.get(key, {})
        status = t_info.get("status", "Pending")
        notes = t_info.get("notes", "").strip()
        sev_str = v.severity.value if hasattr(v.severity, "value") else str(v.severity)

        before_code = v.before_html or v.raw_html_snippet or ""
        after_code = v.after_html or v.suggested_fix or ""

        writer.writerow([
            v.rule_id,
            v.rule_name,
            sev_str,
            status,
            notes,
            v.dom_selector,
            v.issue_explanation,
            before_code,
            after_code,
        ])

    return output.getvalue()


# =========================================================================
# CLI Verification Flag
# =========================================================================
if __name__ == "__main__":
    print("=" * 75)
    print("   AI ACCESSIBILITY AUDITOR: MULTI-FORMAT EXPORTER VERIFICATION CLI")
    print("=" * 75)

    base_dir = Path(__file__).resolve().parent.parent
    sample_file = base_dir / "test_pages" / "01_ecommerce_checkout.html"
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not sample_file.exists():
        print(f"[!] Error: Sample file {sample_file} not found.")
        exit(1)

    print(f"[*] Auditing sample page: {sample_file.name} ...")
    from auditor.rules import audit_page_file
    result = audit_page_file(sample_file)
    print(f"[+] Total Violations Found: {result.total_violations}")

    # Simulate realistic Human QA Triage Workflow:
    # Mark 1 finding as "False Positive" with reviewer note
    # Mark the remaining findings as "Confirmed Defect"
    triage_map: Dict[str, Dict[str, Any]] = {}
    for idx, v in enumerate(result.violations):
        key = get_violation_key(v, idx)
        if idx == 0:
            triage_map[key] = {
                "status": "False Positive",
                "notes": "QA Verified: Decorative icon element; verified with screen reader as non-blocking in checkout flow.",
            }
        else:
            triage_map[key] = {
                "status": "Confirmed Defect",
                "notes": "Confirmed Defect: Critical screen reader or contrast barrier, ticket filed for front-end team.",
            }

    raw_score = calculate_wcag_score(result.violations, {})
    triaged_score = calculate_wcag_score(result.violations, triage_map)
    print(f"[+] Raw Compliance Score: {raw_score}%")
    print(f"[+] Triaged Compliance Score (Excluding False Positives): {triaged_score}%")

    # Generate the 3 export files
    html_out = export_to_html(result, triage_map, page_name=sample_file.name)
    md_out = export_to_markdown(result, triage_map, page_name=sample_file.name)
    csv_out = export_to_csv(result, triage_map)

    html_path = output_dir / "sample_qa_audit_report.html"
    md_path = output_dir / "sample_qa_audit_report.md"
    csv_path = output_dir / "sample_qa_audit_report.csv"

    html_path.write_text(html_out, encoding="utf-8")
    md_path.write_text(md_out, encoding="utf-8")
    csv_path.write_text(csv_out, encoding="utf-8")

    print(f"\n[✓] Generated HTML Report:     {html_path.resolve()} ({len(html_out)} bytes)")
    print(f"[✓] Generated Markdown Report: {md_path.resolve()} ({len(md_out)} bytes)")
    print(f"[✓] Generated CSV Report:      {csv_path.resolve()} ({len(csv_out)} bytes)")
    print("=" * 75)
    print("Multi-Format Report Exporter successfully verified!")
