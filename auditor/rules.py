"""
Deterministic WCAG 2.1 AA Audit Rules Engine.
Implements the 6 core deterministic rules plus cognitive heuristic checks.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag

from auditor.models import Violation, Severity, PageAuditResult
from auditor.contrast import is_contrast_compliant, calculate_contrast_ratio
from auditor.parser import generate_css_selector, parse_html_document, StyleResolver


def _snippet(tag: Tag, max_len: int = 140) -> str:
    """Helper to generate a clean, truncated HTML snippet of a DOM tag."""
    raw = str(tag).strip()
    if len(raw) > max_len:
        # If tag has children, show opening tag and closing
        open_tag = re.match(r"^<[^>]+>", raw)
        if open_tag:
            return f"{open_tag.group(0)} ... </{tag.name}>"
        return raw[:max_len] + "..."
    return raw


# =========================================================================
# Rule 1: Missing Image Alternative Text [WCAG 1.1.1]
# =========================================================================
def audit_missing_image_alt(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    for img in soup.find_all("img"):
        if not img.has_attr("alt"):
            selector = generate_css_selector(img)
            violations.append(
                Violation(
                    rule_id="WCAG-1.1.1",
                    rule_name="Missing Image Alternative Text",
                    severity=Severity.CRITICAL,
                    dom_selector=selector,
                    raw_html_snippet=_snippet(img),
                    issue_explanation=(
                        "The <img> element is missing an 'alt' attribute. Screen readers cannot describe "
                        "the visual content to users with visual impairments and may speak the raw file name."
                    ),
                    suggested_fix='Add a descriptive alt attribute (e.g. alt="Product name and specifications") or alt="" if decorative.',
                )
            )
    return violations


# =========================================================================
# Rule 2: Missing Form Input Labels [WCAG 1.3.1 / WCAG 3.3.2]
# =========================================================================
def audit_form_input_labels(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    excluded_types = {"hidden", "submit", "reset", "button", "image"}

    # Find candidate form controls
    inputs = soup.find_all(["input", "select", "textarea"])

    for ctrl in inputs:
        if ctrl.name == "input" and ctrl.get("type", "text").lower() in excluded_types:
            continue

        ctrl_id = ctrl.get("id", "")
        has_label = False

        # 1. Associated <label for="id">
        if ctrl_id:
            matching_label = soup.find("label", attrs={"for": ctrl_id})
            if matching_label and matching_label.get_text(strip=True):
                has_label = True

        # 2. Wrapped inside <label>
        if not has_label:
            parent_label = ctrl.find_parent("label")
            if parent_label and parent_label.get_text(strip=True):
                has_label = True

        # 3. aria-label
        if not has_label:
            aria_label = ctrl.get("aria-label", "").strip()
            if aria_label:
                has_label = True

        # 4. aria-labelledby
        if not has_label:
            aria_labelledby = ctrl.get("aria-labelledby", "").strip()
            if aria_labelledby:
                target_node = soup.find(id=aria_labelledby)
                if target_node and target_node.get_text(strip=True):
                    has_label = True

        if not has_label:
            selector = generate_css_selector(ctrl)
            placeholder = ctrl.get("placeholder", "")
            explanation = (
                f"Form control <{ctrl.name}> lacks a programmatic label (<label for='...'>, wrapping <label>, or aria-label). "
            )
            if placeholder:
                explanation += (
                    f"Relying solely on placeholder='{placeholder}' violates WCAG 3.3.2 because placeholders "
                    "disappear on input and are not reliably announced by all assistive technologies."
                )
            else:
                explanation += "Assistive technologies cannot announce the purpose of this input field."

            violations.append(
                Violation(
                    rule_id="WCAG-1.3.1",
                    rule_name="Missing Form Input Label",
                    severity=Severity.CRITICAL,
                    dom_selector=selector,
                    raw_html_snippet=_snippet(ctrl),
                    issue_explanation=explanation,
                    suggested_fix=(
                        f'<label for="{ctrl_id or "input-id"}">Descriptive Label</label> or add '
                        f'aria-label="Descriptive Label" to the <{ctrl.name}> element.'
                    ),
                )
            )

    return violations


# =========================================================================
# Rule 3: Insufficient Color Contrast < 4.5:1 [WCAG 1.4.3]
# =========================================================================
def audit_color_contrast(soup: BeautifulSoup, resolver: StyleResolver) -> List[Violation]:
    violations: List[Violation] = []

    # Elements where text contrast is critical: buttons, headings, links, badges, form controls
    candidates = soup.find_all(["button", "a", "span", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6"])

    for el in candidates:
        # Check elements that have direct text or classes indicating styled text
        direct_text = "".join(el.find_all(string=True, recursive=False)).strip()
        has_styled_class = bool(el.get("class")) or bool(el.get("id")) or bool(el.get("style"))

        if not direct_text and not has_styled_class:
            continue

        styles = resolver.get_element_styles(el)
        fg_color = styles.get("color", "")
        bg_color = styles.get("background-color", "")

        # Only evaluate elements where explicit color styling was applied
        if not fg_color or not bg_color:
            continue

        font_size = styles.get("font-size", "16px")
        font_weight = styles.get("font-weight", "400")

        # Determine if large text
        is_large = False
        size_match = re.search(r"([\d\.]+)\s*(px|pt|rem|em)", font_size)
        if size_match:
            val = float(size_match.group(1))
            unit = size_match.group(2)
            if unit in ["rem", "em"]:
                val *= 16.0
            if unit == "pt":
                val *= 1.333
            is_bold = font_weight in ["700", "800", "900", "bold"]
            if val >= 24 or (val >= 18.66 and is_bold):
                is_large = True

        is_compliant, ratio, threshold = is_contrast_compliant(fg_color, bg_color, is_large_text=is_large)

        if not is_compliant and ratio < threshold:
            selector = generate_css_selector(el)
            # Avoid duplicate contrast violations on identical selector
            if any(v.dom_selector == selector and v.rule_id == "WCAG-1.4.3" for v in violations):
                continue

            violations.append(
                Violation(
                    rule_id="WCAG-1.4.3",
                    rule_name="Insufficient Color Contrast Ratio",
                    severity=Severity.SERIOUS,
                    dom_selector=selector,
                    raw_html_snippet=_snippet(el),
                    issue_explanation=(
                        f"Computed contrast ratio is {ratio}:1, which fails WCAG AA minimum threshold of {threshold}:1 "
                        f"(foreground '{fg_color}' on background '{bg_color}'). "
                        "Users with low vision or color perception deficiencies will struggle to read this content."
                    ),
                    suggested_fix=(
                        f"Adjust foreground or background color to achieve at least {threshold}:1 contrast ratio."
                    ),
                )
            )

    return violations


# =========================================================================
# Rule 4: Heading Hierarchy Skips [WCAG 1.3.1]
# =========================================================================
def audit_heading_hierarchy(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    headings = soup.find_all(re.compile(r"^h[1-6]$"))

    last_level = 0
    for h in headings:
        level = int(h.name[1])

        # If previous heading exists and current heading skips more than 1 level
        if last_level > 0 and level > last_level + 1:
            selector = generate_css_selector(h)
            violations.append(
                Violation(
                    rule_id="WCAG-1.3.1",
                    rule_name="Heading Hierarchy Skip",
                    severity=Severity.MODERATE,
                    dom_selector=selector,
                    raw_html_snippet=_snippet(h),
                    issue_explanation=(
                        f"Heading hierarchy skips from <h{last_level}> directly to <h{level}>. "
                        f"Skipping heading levels (e.g. omitting intermediate <h{last_level+1}>) breaks the "
                        "outline structure that screen reader users rely on to build an accurate mental map of page content."
                    ),
                    suggested_fix=f"Change <{h.name}> to <h{last_level+1}> or restructure sectioning to avoid skipped ranks.",
                )
            )

        last_level = level

    return violations


# =========================================================================
# Rule 5: Missing Document Language [WCAG 3.1.1]
# =========================================================================
def audit_document_language(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    html_tag = soup.find("html")

    if not html_tag or not html_tag.has_attr("lang") or not html_tag.get("lang", "").strip():
        selector = "html"
        snippet = "<html>" if not html_tag else str(html_tag)[:60] + "..."
        violations.append(
            Violation(
                rule_id="WCAG-3.1.1",
                rule_name="Missing Document Language Attribute",
                severity=Severity.SERIOUS,
                dom_selector=selector,
                raw_html_snippet=snippet,
                issue_explanation=(
                    "The root <html> element is missing a valid 'lang' attribute. Without a language declaration, "
                    "screen readers and speech synthesizers cannot determine the proper pronunciation rules, "
                    "phonetics, or Braille translation table to apply."
                ),
                suggested_fix='Add a valid BCP 47 language code to the root element, e.g. <html lang="en">.',
            )
        )

    return violations


# =========================================================================
# Rule 6: Invalid ARIA / Non-focusable Interactive Roles [WCAG 4.1.2]
# =========================================================================
def audit_interactive_roles_and_aria(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []

    # 1. Custom interactive roles on non-interactive elements without tabindex
    interactive_roles = {"button", "link", "checkbox", "tab", "menuitem"}
    for el in soup.find_all(attrs={"role": True}):
        role = el.get("role", "").lower()
        if role in interactive_roles and el.name in ["div", "span", "p", "a", "i", "section"]:
            # Check if focusable via keyboard
            if not el.has_attr("tabindex"):
                selector = generate_css_selector(el)
                violations.append(
                    Violation(
                        rule_id="WCAG-4.1.2",
                        rule_name="Non-Focusable Interactive Element",
                        severity=Severity.CRITICAL,
                        dom_selector=selector,
                        raw_html_snippet=_snippet(el),
                        issue_explanation=(
                            f"Element <{el.name} role='{role}'> defines an interactive role but lacks tabindex='0'. "
                            "Keyboard-only users cannot tab to or activate this custom control."
                        ),
                        suggested_fix=f'Replace with native <{role}> or add tabindex="0" and keyboard event handlers (Enter/Space).',
                    )
                )

    # 2. Empty icon-only buttons without accessible name
    for btn in soup.find_all("button"):
        text = btn.get_text(strip=True)
        aria_label = btn.get("aria-label", "").strip()
        aria_labelledby = btn.get("aria-labelledby", "").strip()
        img = btn.find("img")
        has_img_alt = img and bool(img.get("alt", "").strip())

        if not text and not aria_label and not aria_labelledby and not has_img_alt:
            selector = generate_css_selector(btn)
            violations.append(
                Violation(
                    rule_id="WCAG-4.1.2",
                    rule_name="Button Missing Accessible Name",
                    severity=Severity.CRITICAL,
                    dom_selector=selector,
                    raw_html_snippet=_snippet(btn),
                    issue_explanation=(
                        "The <button> contains no readable text, aria-label, or image alt attribute. "
                        "Screen readers will announce an unlabelled button, preventing users from understanding its action."
                    ),
                    suggested_fix='Add an aria-label attribute (e.g. aria-label="Notifications") or include descriptive text.',
                )
            )

    # 3. Positive tabindex disrupting natural sequential focus order (WCAG 2.4.3)
    for el in soup.find_all(attrs={"tabindex": True}):
        tabindex_val = el.get("tabindex")
        try:
            val = int(tabindex_val)
            if val > 0:
                selector = generate_css_selector(el)
                violations.append(
                    Violation(
                        rule_id="WCAG-2.4.3",
                        rule_name="Disruptive Positive Tabindex",
                        severity=Severity.MODERATE,
                        dom_selector=selector,
                        raw_html_snippet=_snippet(el),
                        issue_explanation=(
                            f"Element specifies positive tabindex='{val}'. Using positive tabindex values disrupts natural "
                            "DOM keyboard navigation order and creates unpredictable focus transitions for keyboard users."
                        ),
                        suggested_fix='Set tabindex="0" to insert element into natural tab sequence, or rely on native DOM order.',
                    )
                )
        except ValueError:
            pass

    return violations


# =========================================================================
# Heuristic & Cognitive Rules (Ambiguous Links, Focus Outline)
# =========================================================================
def audit_link_text_and_focus(soup: BeautifulSoup, html_content: str) -> List[Violation]:
    violations: List[Violation] = []
    generic_link_phrases = {"click here", "read more", "learn more", "more details", "here", "link"}

    for a in soup.find_all("a"):
        text = a.get_text(strip=True).lower()
        if text in generic_link_phrases:
            selector = generate_css_selector(a)
            violations.append(
                Violation(
                    rule_id="WCAG-2.4.4",
                    rule_name="Ambiguous Link Text",
                    severity=Severity.MODERATE,
                    dom_selector=selector,
                    raw_html_snippet=_snippet(a),
                    issue_explanation=(
                        f"Link contains ambiguous text '{a.get_text(strip=True)}' without descriptive context. "
                        "Users navigating via screen reader link lists cannot determine the link target out of context."
                    ),
                    suggested_fix='Replace link text with self-describing destination (e.g. "Read the full WCAG technical guidelines").',
                )
            )

    # Detect destructive focus removal (e.g., outline: none !important)
    if re.search(r":focus\s*\{[^}]*outline\s*:\s*none", html_content, re.IGNORECASE):
        violations.append(
            Violation(
                rule_id="WCAG-2.4.7",
                rule_name="Focus Outline Suppressed",
                severity=Severity.SERIOUS,
                dom_selector="head > style",
                raw_html_snippet="outline: none !important;",
                issue_explanation=(
                    "CSS suppresses default keyboard focus outlines (:focus { outline: none; }) without providing "
                    "an accessible high-contrast replacement focus indicator. Sighted keyboard navigators cannot track active focus."
                ),
                suggested_fix="Ensure interactive elements retain a high-visibility focus ring, e.g. :focus-visible { outline: 3px solid #2563eb; }.",
            )
        )

    return violations


# =========================================================================
# Orchestrator
# =========================================================================
def audit_html_content(html_content: str, page_name: str = "document", file_path: str = "") -> PageAuditResult:
    """
    Executes the full suite of WCAG 2.1 AA deterministic rules against parsed HTML.
    Returns a structured PageAuditResult.
    """
    soup, resolver = parse_html_document(html_content, file_path=file_path)

    all_violations: List[Violation] = []
    all_violations.extend(audit_document_language(soup))
    all_violations.extend(audit_missing_image_alt(soup))
    all_violations.extend(audit_form_input_labels(soup))
    all_violations.extend(audit_color_contrast(soup, resolver))
    all_violations.extend(audit_heading_hierarchy(soup))
    all_violations.extend(audit_interactive_roles_and_aria(soup))
    all_violations.extend(audit_link_text_and_focus(soup, html_content))

    by_severity: Dict[str, int] = {
        Severity.CRITICAL.value: 0,
        Severity.SERIOUS.value: 0,
        Severity.MODERATE.value: 0,
        Severity.MINOR.value: 0,
    }

    for v in all_violations:
        by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1

    status = "PASSED" if len(all_violations) == 0 else "FAILED"

    return PageAuditResult(
        page_name=page_name,
        file_path=file_path,
        total_violations=len(all_violations),
        violations_by_severity=by_severity,
        violations=all_violations,
        status=status,
    )


def audit_page_file(file_path: Path | str) -> PageAuditResult:
    """Convenience function to audit an HTML file on disk."""
    path = Path(file_path)
    html_content = path.read_text(encoding="utf-8")
    return audit_html_content(html_content, page_name=path.name, file_path=str(path.resolve()))
