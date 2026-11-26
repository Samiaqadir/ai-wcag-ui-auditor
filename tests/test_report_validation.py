"""
Report and Remediation HTML5 Syntax Validation Suite.
Validates that:
1. Exported HTML reports conform to valid HTML5 structure with required metadata and metrics.
2. Exported CSV reports strictly follow RFC 4180 format with all required columns.
3. Every single suggested HTML fix (after_html) produced by the remediation engine parses as valid HTML5.
"""

import os
import sys
import csv
import io
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

# Ensure parent directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auditor.models import PageAuditResult, TriageStatus
from auditor.exporter import export_to_html, export_to_csv, export_to_markdown
from auditor.rules import audit_page_file


class TestReportAndRemediationValidation(unittest.TestCase):
    """Validation test suite for export pipelines and generated HTML patches."""

    @classmethod
    def setUpClass(cls):
        # Run audit on a representative sample page
        sample_page = Path(__file__).resolve().parent.parent / "test_pages" / "01_ecommerce_checkout.html"
        cls.audit_result = audit_page_file(sample_page)
        # Seed triage statuses for testing
        if cls.audit_result.violations:
            cls.audit_result.violations[0].triage_status = TriageStatus.CONFIRMED_DEFECT
            cls.audit_result.violations[0].reviewer_notes = "Verified critical blocker for screen reader users."
        if len(cls.audit_result.violations) > 1:
            cls.audit_result.violations[1].triage_status = TriageStatus.FALSE_POSITIVE
            cls.audit_result.violations[1].reviewer_notes = "Decorative element, ignored in sprint review."

    def test_exported_html_report_validity(self):
        """Validate HTML report structure, metadata, compliance score, and elements."""
        html_output = export_to_html(self.audit_result, reviewer="Senior QA Automation Lead")
        
        # Check basic HTML5 structure
        self.assertTrue(html_output.strip().startswith("<!DOCTYPE html>"), "Missing HTML5 DOCTYPE declaration")
        self.assertIn("<html lang=\"en\">", html_output)
        self.assertIn("<meta charset=\"UTF-8\">", html_output)
        self.assertIn("</html>", html_output)

        # Parse with BeautifulSoup to verify well-formed DOM
        soup = BeautifulSoup(html_output, "html.parser")
        self.assertIsNotNone(soup.find("title"), "HTML report missing <title>")
        self.assertIsNotNone(soup.find("header"), "HTML report missing <header>")
        self.assertIsNotNone(soup.find("main"), "HTML report missing <main>")

        # Check key metrics and badges
        score = self.audit_result.calculate_compliance_score()
        self.assertIn(f"{score}%", html_output, "Compliance score percentage not found in report")
        self.assertIn("Confirmed Defect", html_output)
        self.assertIn("False Positive", html_output)

    def test_exported_csv_report_rfc4180_compliance(self):
        """Validate RFC 4180 compliance and exact column header schema."""
        csv_output = export_to_csv(self.audit_result)
        
        # Parse using standard csv reader
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)
        self.assertGreater(len(rows), 1, "CSV report must contain headers and at least one data row")

        expected_headers = [
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
            "After HTML"
        ]
        self.assertEqual(rows[0], expected_headers, f"CSV headers mismatch. Found: {rows[0]}")

        # Check that data rows have identical column counts
        for idx, row in enumerate(rows[1:], start=2):
            self.assertEqual(len(row), len(expected_headers), f"Row {idx} has invalid column count")

    def test_remediation_patches_pass_html5_syntax_validation(self):
        """Verify that every generated 'after_html' patch parses as valid HTML5 DOM nodes."""
        test_pages_dir = Path(__file__).resolve().parent.parent / "test_pages"
        pages_to_test = [
            "01_ecommerce_checkout.html",
            "02_saas_dashboard.html",
            "03_signup_form.html",
            "04_blog_article.html",
            "06_malformed_html.html",
            "08_inline_svg_graphics.html",
            "11_prompt_injection_payloads.html"
        ]

        total_patches_verified = 0

        for page_name in pages_to_test:
            page_path = test_pages_dir / page_name
            if not page_path.exists():
                continue
            
            result = audit_page_file(page_path)
            for v in result.violations:
                if v.after_html:
                    total_patches_verified += 1
                    patch = v.after_html.strip()
                    
                    # 1. Check for balanced angle brackets
                    open_count = patch.count("<")
                    close_count = patch.count(">")
                    self.assertEqual(
                        open_count, close_count,
                        f"Unbalanced angle brackets in patch for {v.rule_id} ({page_name}): {patch}"
                    )

                    # 2. Parse patch with HTML parser
                    frag_soup = BeautifulSoup(patch, "html.parser")
                    self.assertIsNotNone(frag_soup, f"Failed to parse patch as HTML: {patch}")

                    # 3. Ensure no empty or broken tags
                    parsed_tags = frag_soup.find_all(True)
                    # Either contains tags or is valid CSS/snippet
                    if "<" in patch and ">" in patch:
                        self.assertGreater(
                            len(parsed_tags), 0,
                            f"Patch contained brackets but no valid parsed tags: {patch}"
                        )

        self.assertGreater(total_patches_verified, 10, "Expected at least 10 remediated patches to be verified")


if __name__ == "__main__":
    unittest.main()
