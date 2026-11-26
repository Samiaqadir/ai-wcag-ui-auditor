"""
Comprehensive 12-Case WCAG & UI Regression Suite Runner.
Executes automated accessibility audits across all 12 test fixtures,
verifying 0 false-positive criticals on compliant pages, resilient parser behavior,
and generating the 12-Case Regression Matrix.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Ensure workspace root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auditor.models import PageAuditResult, Severity
from auditor.rules import audit_page_file

TEST_CASES = [
    {
        "id": "TC-01",
        "file": "01_ecommerce_checkout.html",
        "category": "Baseline E-Commerce",
        "focus": "Product image alt, low button contrast, form labels",
        "expect_compliant": False
    },
    {
        "id": "TC-02",
        "file": "02_saas_dashboard.html",
        "category": "Baseline SaaS Dashboard",
        "focus": "Heading hierarchy skips, unlabelled icon buttons, contrast badge",
        "expect_compliant": False
    },
    {
        "id": "TC-03",
        "file": "03_signup_form.html",
        "category": "Baseline Signup Form",
        "focus": "Placeholder-only labels, ARIA role mismatch, positive tabindex",
        "expect_compliant": False
    },
    {
        "id": "TC-04",
        "file": "04_blog_article.html",
        "category": "Baseline Blog Article",
        "focus": "Missing lang attribute, ambiguous links, focus outline suppressed",
        "expect_compliant": False
    },
    {
        "id": "TC-05",
        "file": "05_accessible_reference.html",
        "category": "Compliant Reference Portal",
        "focus": "Full WCAG 2.1 AA compliance - verify 0 false-positive criticals",
        "expect_compliant": True
    },
    {
        "id": "TC-06",
        "file": "06_malformed_html.html",
        "category": "Malformed & Non-standard HTML",
        "focus": "Unclosed tags, unquoted attributes, mismatched elements - parser resilience",
        "expect_compliant": False
    },
    {
        "id": "TC-07",
        "file": "07_empty_body.html",
        "category": "Empty Document Body",
        "focus": "Zero content edge case - verify no crash, 0 false-positive criticals",
        "expect_compliant": True
    },
    {
        "id": "TC-08",
        "file": "08_inline_svg_graphics.html",
        "category": "Inline SVG Graphics",
        "focus": "SVG <title>, aria-labelledby, decorative SVGs, unlabelled SVG button",
        "expect_compliant": False
    },
    {
        "id": "TC-09",
        "file": "09_deeply_nested_tables.html",
        "category": "Deeply Nested Table Architecture",
        "focus": "4-tier nested data & layout tables, table caption, th scopes",
        "expect_compliant": True
    },
    {
        "id": "TC-10",
        "file": "10_already_compliant_portal.html",
        "category": "Compliant Enterprise HR Portal",
        "focus": "Production portal with complete landmarks - verify 0 false-positive criticals",
        "expect_compliant": True
    },
    {
        "id": "TC-11",
        "file": "11_prompt_injection_payloads.html",
        "category": "Adversarial Security Payloads",
        "focus": "Prompt injection in comments, alt tags, and javascript schemes",
        "expect_compliant": False
    },
    {
        "id": "TC-12",
        "file": "12_dynamic_js_edge_cases.html",
        "category": "Dynamic Client SPA & Hidden Nodes",
        "focus": "display:none, visibility:hidden, <template> tags - hidden contrast filtering",
        "expect_compliant": True
    },
]


def run_12_case_suite() -> Dict[str, Any]:
    test_pages_dir = Path(__file__).resolve().parent.parent / "test_pages"
    results = []
    all_passed = True
    start_time = time.time()

    print("\n" + "=" * 90)
    print("AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor - 12-Case Regression Suite")
    print("=" * 90)

    for tc in TEST_CASES:
        file_path = test_pages_dir / tc["file"]
        if not file_path.exists():
            print(f"[-] ERROR: File not found {file_path}")
            all_passed = False
            continue

        try:
            audit_res = audit_page_file(file_path)
            critical_count = audit_res.violations_by_severity.get(Severity.CRITICAL.value, 0)
            total_findings = audit_res.total_violations

            # Verification rule: Compliant pages MUST have 0 critical violations
            if tc["expect_compliant"]:
                case_passed = (critical_count == 0)
            else:
                # Broken / edge-case pages must be audited without crashing and identify violations
                case_passed = (total_findings > 0)

            if not case_passed:
                all_passed = False

            results.append({
                "id": tc["id"],
                "file": tc["file"],
                "category": tc["category"],
                "focus": tc["focus"],
                "total_violations": total_findings,
                "critical": critical_count,
                "serious": audit_res.violations_by_severity.get(Severity.SERIOUS.value, 0),
                "moderate": audit_res.violations_by_severity.get(Severity.MODERATE.value, 0),
                "minor": audit_res.violations_by_severity.get(Severity.MINOR.value, 0),
                "expect_compliant": tc["expect_compliant"],
                "passed": case_passed,
                "status": "PASS" if case_passed else "FAIL",
                "zero_criticals_verified": (critical_count == 0)
            })

            status_str = "[PASS]" if case_passed else "[FAIL]"
            print(f"{status_str} {tc['id']} | {tc['file']:<35} | Violations: {total_findings:2d} (Critical: {critical_count:2d})")

        except Exception as e:
            all_passed = False
            print(f"[FAIL] {tc['id']} | {tc['file']:<35} | CRASH / EXCEPTION: {e}")
            results.append({
                "id": tc["id"],
                "file": tc["file"],
                "category": tc["category"],
                "focus": tc["focus"],
                "total_violations": -1,
                "critical": -1,
                "status": "CRASH",
                "passed": False,
                "error": str(e)
            })

    elapsed = time.time() - start_time
    print("=" * 90)
    print(f"Summary: 12 Cases Evaluated in {elapsed:.2f}s | Overall Result: {'ALL 12 CASES PASSED' if all_passed else 'SOME CASES FAILED'}")
    print("=" * 90 + "\n")

    # Save output matrix
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_file = output_dir / "12_case_regression_matrix.json"
    matrix_file.write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "all_passed": all_passed,
        "elapsed_seconds": round(elapsed, 2),
        "cases": results
    }, indent=2), encoding="utf-8")

    return {
        "all_passed": all_passed,
        "cases": results,
        "elapsed": round(elapsed, 2)
    }


if __name__ == "__main__":
    result = run_12_case_suite()
    if not result["all_passed"]:
        sys.exit(1)
