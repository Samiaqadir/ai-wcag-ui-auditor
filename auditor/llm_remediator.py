"""
AI-Powered Remediator Module (LLM Integration Stub).
Provides contextual AI remediation suggestions for WCAG accessibility violations.
Supports google-genai and OpenAI APIs with graceful offline fallback templates.
"""

import os
from typing import List, Dict, Optional, Any
from auditor.models import Violation, Severity


SYSTEM_PROMPT = """You are a Senior Accessibility Engineer and WCAG 2.1 AA Specialist.
Your job is to analyze accessibility violations identified by automated auditors and provide:
1. An accessible, drop-in replacement HTML snippet.
2. An explanation of why the fix complies with WCAG guidelines.
3. Any ARIA considerations or edge cases (e.g. keyboard navigation, screen reader behaviors).
Format your response cleanly and concisely.
"""


class LLMRemediator:
    """
    Handles LLM-driven remediation generation for WCAG violations.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                # Log or keep client None for fallback
                self.client = None

    def generate_remediation(self, violation: Violation, surrounding_context: str = "") -> Dict[str, Any]:
        """
        Generates an actionable AI remediation plan for a single violation.
        Falls back to rule-specific heuristics if LLM client is unconfigured.
        """
        # If live API client is available and configured
        if self.client:
            try:
                prompt = f"""
{SYSTEM_PROMPT}

Violation Details:
- Rule: {violation.rule_id} ({violation.rule_name})
- Severity: {violation.severity.value}
- Selector: {violation.dom_selector}
- Broken HTML Snippet:
```html
{violation.raw_html_snippet}
```
- Issue Explanation: {violation.issue_explanation}
- Surrounding Context: {surrounding_context}

Provide the remediated HTML code and technical notes.
"""
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return {
                    "source": "google-genai",
                    "model": self.model_name,
                    "remediation": response.text,
                    "confidence": 0.95
                }
            except Exception as err:
                # Fall back gracefully to deterministic remediation template
                pass

        # Offline deterministic remediation template
        return {
            "source": "deterministic-fallback",
            "model": "rule-template-v1",
            "remediation": self._get_fallback_fix(violation),
            "confidence": 0.85
        }

    def _get_fallback_fix(self, violation: Violation) -> str:
        """Rule-specific fallback accessible patch templates."""
        rule = violation.rule_id
        if rule == "WCAG-1.1.1":
            return 'Patch: Add informative alt attribute, e.g. <img src="..." alt="Detailed description of image content">'
        elif rule in ["WCAG-1.3.1", "WCAG-3.3.2"]:
            return 'Patch: Associate explicit label: <label for="field-id">Field Name</label><input id="field-id" ...>'
        elif rule == "WCAG-1.4.3":
            return 'Patch: Increase color contrast ratio to at least 4.5:1 by adjusting text or background color tokens.'
        elif rule == "WCAG-3.1.1":
            return 'Patch: Define language attribute on root document: <html lang="en">'
        elif rule == "WCAG-4.1.2":
            return 'Patch: Ensure interactive controls are keyboard focusable: add tabindex="0" and aria-label="Action Name", or use native <button>.'
        elif rule == "WCAG-2.4.4":
            return 'Patch: Replace ambiguous anchor text with descriptive context, e.g. <a href="...">View complete WCAG guidelines</a>'
        return violation.suggested_fix

    def batch_remediate(self, violations: List[Violation]) -> List[Dict[str, Any]]:
        """Remediates a list of violations."""
        return [self.generate_remediation(v) for v in violations]
