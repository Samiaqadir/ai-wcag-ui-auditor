"""
Multi-Format QA Report Exporter.
Exports audited and human-triaged accessibility findings into:
1. Executive Self-Contained HTML Report
2. GitHub/Jira-Ready Markdown Report
3. Structured Flat CSV Table
"""

import csv
import io
import html
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

from auditor.models import PageAuditResult, Violation, Severity, TriageStatus


def export_to_html(result: PageAuditResult, report_title: Optional[str] = None, reviewer: Optional[str] = None) -> str:
    """
    Generates a self-contained, print-ready, modern HTML audit report.
    Includes compliance score gauge, triage badges, reviewer notes, and Before/After diffs.
    """
    title = report_title or f"WCAG 2.1 AA Executive QA Audit Report - {result.page_name}"
    score = result.calculate_compliance_score()
    reviewer_str = f" &bull; <strong>Reviewer:</strong> {html.escape(reviewer)}" if reviewer else ""
    
    # Calculate triage counts
    total = len(result.violations)
    confirmed = sum(1 for v in result.violations if v.triage_status == TriageStatus.CONFIRMED_DEFECT)
    false_positives = sum(1 for v in result.violations if v.triage_status == TriageStatus.FALSE_POSITIVE)
    wont_fix = sum(1 for v in result.violations if v.triage_status == TriageStatus.WONT_FIX)
    pending = sum(1 for v in result.violations if v.triage_status == TriageStatus.PENDING)

    # Score color
    score_color = "#16a34a" if score >= 85 else ("#d97706" if score >= 60 else "#dc2626")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --border: #e2e8f0;
      --text: #0f172a;
      --text-muted: #64748b;
      --primary: #4f46e5;
      --critical: #dc2626;
      --serious: #d97706;
      --moderate: #0284c7;
      --success: #16a34a;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2.5rem 1.5rem;
    }}
    .report-container {{
      max-width: 1040px;
      margin: 0 auto;
    }}
    .header-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 2rem;
      margin-bottom: 2rem;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 2rem;
    }}
    .header-left h1 {{
      font-size: 1.75rem;
      font-weight: 800;
      color: var(--text);
      margin-bottom: 0.5rem;
    }}
    .meta-line {{
      font-size: 0.875rem;
      color: var(--text-muted);
    }}
    .score-badge {{
      background: #f1f5f9;
      border: 3px solid {score_color};
      border-radius: 50%;
      width: 110px;
      height: 110px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      flex-shrink: 0;
    }}
    .score-val {{
      font-size: 1.85rem;
      font-weight: 800;
      color: {score_color};
      line-height: 1;
    }}
    .score-label {{
      font-size: 0.65rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1.25rem;
      text-align: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }}
    .kpi-num {{
      font-size: 1.8rem;
      font-weight: 800;
      margin-bottom: 0.25rem;
    }}
    .kpi-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.05em;
    }}
    .findings-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
    }}
    .findings-title {{
      font-size: 1.35rem;
      font-weight: 700;
    }}
    .violation-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 2px 4px rgba(0,0,0,0.03);
      page-break-inside: avoid;
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
    }}
    .rule-tag {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--primary);
    }}
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .badge-critical {{ background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }}
    .badge-serious {{ background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }}
    .badge-moderate {{ background: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd; }}
    .badge-minor {{ background: #f8fafc; color: #64748b; border: 1px solid #cbd5e1; }}
    
    .badge-triage-confirmed {{ background: #fee2e2; color: #991b1b; border: 1px solid #f87171; }}
    .badge-triage-false {{ background: #dcfce7; color: #166534; border: 1px solid #86efac; }}
    .badge-triage-wontfix {{ background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }}
    .badge-triage-pending {{ background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }}

    .card-title {{
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }}
    .selector-box {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.785rem;
      background: #f1f5f9;
      padding: 0.4rem 0.65rem;
      border-radius: 6px;
      color: #475569;
      margin-bottom: 0.75rem;
      word-break: break-all;
    }}
    .desc-text {{
      font-size: 0.9rem;
      color: #334155;
      margin-bottom: 1rem;
    }}
    .notes-box {{
      background: #f8fafc;
      border-left: 4px solid var(--primary);
      padding: 0.75rem 1rem;
      margin-bottom: 1rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.85rem;
      color: #1e293b;
    }}
    .diff-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-top: 1rem;
    }}
    .diff-col h4 {{
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.4rem;
    }}
    .diff-code {{
      background: #0f172a;
      color: #f8fafc;
      padding: 0.85rem;
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.785rem;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
      min-height: 70px;
    }}
    .diff-code.before {{ border-left: 4px solid var(--critical); }}
    .diff-code.after {{ border-left: 4px solid var(--success); }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .header-card, .violation-card {{ box-shadow: none; border-color: #cbd5e1; }}
    }}
  </style>
</head>
<body>
  <div class="report-container">
    <header class="header-card">
      <div class="header-left">
        <h1>{html.escape(title)}</h1>
        <div class="meta-line">
          <strong>Audited Page:</strong> {html.escape(result.page_name)} &bull; 
          <strong>Date:</strong> {html.escape(result.timestamp)} &bull;
          <strong>Status:</strong> {html.escape(result.status)}{reviewer_str}
        </div>
      </div>
      <div class="score-badge">
        <div class="score-val">{score}%</div>
        <div class="score-label">Compliance</div>
      </div>
    </header>

    <main class="report-main">
      <section class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-num">{total}</div>
        <div class="kpi-label">Total Findings</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num" style="color: #dc2626;">{confirmed}</div>
        <div class="kpi-label">Confirmed Defects</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num" style="color: #16a34a;">{false_positives}</div>
        <div class="kpi-label">False Positives</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num" style="color: #4f46e5;">{wont_fix + pending}</div>
        <div class="kpi-label">Pending / Won't Fix</div>
      </div>
    </section>

    <section>
      <div class="findings-header">
        <h2 class="findings-title">Detailed WCAG 2.1 AA Findings & Triage Log</h2>
        <span style="font-size: 0.85rem; color: var(--text-muted);">{len(result.violations)} issues documented</span>
      </div>
"""

    for idx, v in enumerate(result.violations, 1):
        sev_class = f"badge-{v.severity.value.lower()}"
        
        triage_class = "badge-triage-pending"
        if v.triage_status == TriageStatus.CONFIRMED_DEFECT:
            triage_class = "badge-triage-confirmed"
        elif v.triage_status == TriageStatus.FALSE_POSITIVE:
            triage_class = "badge-triage-false"
        elif v.triage_status == TriageStatus.WONT_FIX:
            triage_class = "badge-triage-wontfix"

        notes_html = ""
        if v.reviewer_notes:
            notes_html = f"""
            <div class="notes-box">
              <strong>QA Reviewer Note:</strong> {html.escape(v.reviewer_notes)}
            </div>
            """

        html_content += f"""
      <article class="violation-card">
        <div class="card-top">
          <span class="rule-tag">#{idx} &bull; {html.escape(v.rule_id)}</span>
          <div>
            <span class="badge {sev_class}">{html.escape(v.severity.value)}</span>
            <span class="badge {triage_class}" style="margin-left: 0.4rem;">{html.escape(v.triage_status.value)}</span>
          </div>
        </div>
        <h3 class="card-title">{html.escape(v.rule_name)}</h3>
        <div class="selector-box">Selector: {html.escape(v.dom_selector)}</div>
        <p class="desc-text">{html.escape(v.issue_explanation)}</p>
        
        {notes_html}

        <div class="diff-grid">
          <div class="diff-col">
            <h4 style="color: var(--critical);">🔴 Non-Compliant HTML (Before)</h4>
            <div class="diff-code before">{html.escape(v.before_html or v.raw_html_snippet)}</div>
          </div>
          <div class="diff-col">
            <h4 style="color: var(--success);">🟢 Accessible Patch (After)</h4>
            <div class="diff-code after">{html.escape(v.after_html or v.suggested_fix)}</div>
          </div>
        </div>
      </article>
"""

    html_content += """
      </section>
    </main>
  </div>
</body>
</html>
"""
    return html_content


def export_to_markdown(result: PageAuditResult, report_title: Optional[str] = None) -> str:
    """
    Generates a clean GitHub/Jira-ready Markdown QA report with triage commentary.
    """
    title = report_title or f"WCAG 2.1 AA QA Audit Report: {result.page_name}"
    score = result.calculate_compliance_score()

    total = len(result.violations)
    confirmed = sum(1 for v in result.violations if v.triage_status == TriageStatus.CONFIRMED_DEFECT)
    false_positives = sum(1 for v in result.violations if v.triage_status == TriageStatus.FALSE_POSITIVE)
    wont_fix = sum(1 for v in result.violations if v.triage_status == TriageStatus.WONT_FIX)
    pending = sum(1 for v in result.violations if v.triage_status == TriageStatus.PENDING)

    lines = [
        f"# {title}",
        "",
        f"- **Audited Page:** `{result.page_name}`",
        f"- **Audit Date:** `{result.timestamp}`",
        f"- **WCAG 2.1 AA Compliance Score:** `{score}%`",
        f"- **Overall Status:** `{result.status}`",
        "",
        "## Executive Summary & QA Triage KPIs",
        "",
        "| Total Findings | Confirmed Defects | False Positives | Pending / Won't Fix | Compliance Score |",
        "| :---: | :---: | :---: | :---: | :---: |",
        f"| **{total}** | **{confirmed}** | **{false_positives}** | **{pending + wont_fix}** | **{score}%** |",
        "",
        "---",
        "",
        "## Detailed Triage Findings & Remediation Patches",
        "",
    ]

    for idx, v in enumerate(result.violations, 1):
        lines.append(f"### {idx}. {v.rule_name} (`{v.rule_id}`)")
        lines.append(f"- **Severity:** `{v.severity.value}`")
        lines.append(f"- **QA Triage Status:** `{v.triage_status.value}`")
        lines.append(f"- **Target DOM Selector:** `{v.dom_selector}`")
        lines.append(f"- **Issue:** {v.issue_explanation}")
        if v.reviewer_notes:
            lines.append(f"- **QA Reviewer Notes:** *{v.reviewer_notes}*")
        lines.append("")
        lines.append("#### 🔴 Before (Violating HTML):")
        lines.append("```html")
        lines.append(v.before_html or v.raw_html_snippet)
        lines.append("```")
        lines.append("")
        lines.append("#### 🟢 After (Remediated Accessible Patch):")
        lines.append("```html")
        lines.append(v.after_html or v.suggested_fix)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def export_to_csv(result: PageAuditResult) -> str:
    """
    Exports findings and triage decisions as a structured CSV string.
    Ready for import into Jira, Excel, or test management suites.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header Row
    writer.writerow([
        "Page Name",
        "Rule ID",
        "Rule Name",
        "Severity",
        "Triage Status",
        "Reviewer Notes",
        "DOM Selector",
        "Issue Explanation",
        "Suggested Fix",
        "Before HTML",
        "After HTML",
    ])

    for v in result.violations:
        writer.writerow([
            result.page_name,
            v.rule_id,
            v.rule_name,
            v.severity.value,
            v.triage_status.value,
            v.reviewer_notes,
            v.dom_selector,
            v.issue_explanation,
            v.suggested_fix,
            v.before_html or v.raw_html_snippet,
            v.after_html or v.suggested_fix,
        ])

    return output.getvalue()


# =========================================================================
# Verification Script / CLI Simulation
# =========================================================================
def run_sample_qa_export():
    """
    Simulates a QA triage session on 01_ecommerce_checkout.html,
    marking 1 finding as False Positive with notes and confirming the rest,
    then saves sample HTML, Markdown, and CSV reports to /output/.
    """
    from auditor.rules import audit_page_file

    base_dir = Path(__file__).resolve().parent.parent
    sample_page = base_dir / "test_pages" / "01_ecommerce_checkout.html"
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Auditing {sample_page.name} for QA export simulation...")
    result = audit_page_file(sample_page)

    # Simulate QA Triage Workflow:
    # Mark finding #2 as False Positive with reviewer note
    # Confirm others as Confirmed Defect
    for idx, v in enumerate(result.violations):
        if idx == 1:  # Second item
            v.triage_status = TriageStatus.FALSE_POSITIVE
            v.reviewer_notes = "Verified: Secondary decorative thumbnail; verified with NVDA screen reader that product title in heading h3 adequately describes item."
        else:
            v.triage_status = TriageStatus.CONFIRMED_DEFECT
            v.reviewer_notes = "Confirmed Defect: Meets WCAG AA failure criteria; ticket filed in sprint backlog for frontend remediation."

    # Export to HTML
    html_out = output_dir / "sample_qa_audit_report.html"
    html_out.write_text(export_to_html(result), encoding="utf-8")
    print(f"[+] Exported HTML report:     {html_out.resolve()}")

    # Export to Markdown
    md_out = output_dir / "sample_qa_audit_report.md"
    md_out.write_text(export_to_markdown(result), encoding="utf-8")
    print(f"[+] Exported Markdown report: {md_out.resolve()}")

    # Export to CSV
    csv_out = output_dir / "sample_qa_audit_report.csv"
    csv_out.write_text(export_to_csv(result), encoding="utf-8")
    print(f"[+] Exported CSV table:       {csv_out.resolve()}")

    score = result.calculate_compliance_score()
    print(f"[✓] Verification complete. Dynamic Compliance Score: {score}% (Excluding False Positives)")


if __name__ == "__main__":
    run_sample_qa_export()
