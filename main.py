"""
CLI Entry Point for the AI Accessibility (WCAG) & UI Regression Auditor.
Scans test pages, executes the deterministic engine, prints a terminal summary,
and outputs the structured JSON report.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

from auditor.models import AuditSummaryReport, PageAuditResult, Severity
from auditor.rules import audit_page_file


def format_terminal_banner():
    banner = """
================================================================================
          AI ACCESSIBILITY (WCAG 2.1 AA) & UI REGRESSION AUDITOR
                             Day-1 Audit Engine
================================================================================
"""
    return banner


def main():
    print(format_terminal_banner())

    base_dir = Path(__file__).resolve().parent
    test_pages_dir = base_dir / "test_pages"
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not test_pages_dir.exists():
        print(f"[ERROR] Test directory not found at: {test_pages_dir}")
        sys.exit(1)

    html_files = sorted(test_pages_dir.glob("*.html"))
    if not html_files:
        print(f"[ERROR] No HTML test files found in: {test_pages_dir}")
        sys.exit(1)

    print(f"[*] Discovered {len(html_files)} test pages to audit in {test_pages_dir.name}/")
    print("-" * 80)

    page_results = []
    total_violations = 0
    passed_count = 0
    failed_count = 0
    severity_totals = {
        Severity.CRITICAL.value: 0,
        Severity.SERIOUS.value: 0,
        Severity.MODERATE.value: 0,
        Severity.MINOR.value: 0,
    }

    # Execute audits
    for idx, page_path in enumerate(html_files, 1):
        print(f"[{idx}/{len(html_files)}] Auditing: {page_path.name} ... ", end="")
        result = audit_page_file(page_path)
        page_results.append(result)

        if result.status == "PASSED":
            passed_count += 1
            print("\033[92mPASSED (0 violations)\033[0m")
        else:
            failed_count += 1
            print(f"\033[91mFAILED ({result.total_violations} violations)\033[0m")

        total_violations += result.total_violations
        for sev, count in result.violations_by_severity.items():
            severity_totals[sev] = severity_totals.get(sev, 0) + count

    # Detailed Violations Breakdown
    print("\n" + "=" * 80)
    print("                      DETAILED AUDIT BREAKDOWN BY PAGE")
    print("=" * 80)

    for res in page_results:
        status_color = "\033[92m" if res.status == "PASSED" else "\033[91m"
        print(f"\nDocument: \033[1m{res.page_name}\033[0m  Status: {status_color}[{res.status}]\033[0m  Violations: {res.total_violations}")
        if res.violations:
            print(f"  {'-' * 76}")
            print(f"  {'RULE ID':<14} | {'SEVERITY':<10} | {'SELECTOR':<26} | {'ISSUE SUMMARY'}")
            print(f"  {'-' * 76}")
            for v in res.violations:
                sev_color = "\033[91m" if v.severity == Severity.CRITICAL else ("\033[93m" if v.severity == Severity.SERIOUS else "\033[36m")
                selector_display = v.dom_selector if len(v.dom_selector) <= 26 else v.dom_selector[:23] + "..."
                summary = v.issue_explanation[:48] + "..." if len(v.issue_explanation) > 48 else v.issue_explanation
                print(f"  {v.rule_id:<14} | {sev_color}{v.severity.value:<10}\033[0m | {selector_display:<26} | {summary}")

    # Summary Metrics Table
    print("\n" + "=" * 80)
    print("                              AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total Pages Scanned:      {len(html_files)}")
    print(f"Compliant Pages (Passed): \033[92m{passed_count}\033[0m")
    print(f"Failing Pages (Defects):  \033[91m{failed_count}\033[0m")
    print(f"Total Violations Caught:  {total_violations}")
    print("-" * 80)
    print("Violations by Severity Breakdown:")
    print(f"  - \033[91mCritical:\033[0m {severity_totals.get(Severity.CRITICAL.value, 0)}")
    print(f"  - \033[93mSerious:\033[0m  {severity_totals.get(Severity.SERIOUS.value, 0)}")
    print(f"  - \033[36mModerate:\033[0m {severity_totals.get(Severity.MODERATE.value, 0)}")
    print(f"  - Minor:    {severity_totals.get(Severity.MINOR.value, 0)}")
    print("=" * 80)

    # Compile Structured Report
    summary_report = AuditSummaryReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        engine_version="1.0.0-day1",
        total_pages_scanned=len(html_files),
        passed_pages=passed_count,
        failed_pages=failed_count,
        total_violations=total_violations,
        violations_by_severity=severity_totals,
        results=page_results,
    )

    # Save to JSON
    report_file = output_dir / "initial_audit_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary_report.model_dump(), f, indent=2)

    print(f"\n[+] Structured JSON report successfully saved to:\n    {report_file.resolve()}\n")

    # Verification Assertions
    ref_page = next((r for r in page_results if "05_accessible_reference" in r.page_name), None)
    if ref_page and ref_page.total_violations == 0:
        print("\033[92m[VERIFIED] 05_accessible_reference.html achieved 100% WCAG 2.1 AA compliance (0 violations)!\033[0m")
    else:
        print("\033[91m[WARNING] 05_accessible_reference.html did not report 0 violations!\033[0m")

    distinct_rules = {v.rule_id for r in page_results for v in r.violations}
    print(f"[VERIFIED] Caught {len(distinct_rules)} distinct WCAG rules across test suite: {sorted(list(distinct_rules))}")

    return 0 if (failed_count > 0 and ref_page and ref_page.total_violations == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
