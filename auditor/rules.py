"""
Complete 10-Rule WCAG 2.1 AA Audit Rules Engine.
Includes 6 Deterministic Rules and 4 AI / Heuristic-Assisted Rules,
utilizing Playwright runtime computed styles, bounding boxes, and simulated Tab sequence.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag

from auditor.models import Violation, Severity, PageAuditResult
from auditor.contrast import is_contrast_compliant, calculate_contrast_ratio
from auditor.parser import generate_css_selector, PlaywrightDOMInspector, PageInspectionResult


def _clean_snippet(tag: Tag, max_len: int = 160) -> str:
    """Produces clean raw HTML snippet from a BeautifulSoup tag."""
    raw = str(tag).strip()
    if len(raw) > max_len:
        open_match = re.match(r"^<[^>]+>", raw)
        if open_match:
            return f"{open_match.group(0)} ... </{tag.name}>"
        return raw[:max_len] + "..."
    return raw


# =========================================================================
# Rule 1: Missing Image Alternative Text [WCAG-1.1.1] (Deterministic)
# =========================================================================
def audit_missing_image_alt(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    for img in soup.find_all("img"):
        # If inside inert <template> or explicitly decorative via presentation role or aria-hidden, skip
        if img.find_parent("template") or img.get("role") in ["presentation", "none"] or img.get("aria-hidden") == "true":
            continue
        if not img.has_attr("alt"):
            selector = generate_css_selector(img)
            snippet = _clean_snippet(img)
            violations.append(
                Violation(
                    rule_id="WCAG-1.1.1",
                    rule_name="Missing Image Alternative Text",
                    severity=Severity.CRITICAL,
                    dom_selector=selector,
                    raw_html_snippet=snippet,
                    issue_explanation=(
                        "The <img> element is completely missing an 'alt' attribute. Screen readers cannot describe "
                        "the visual content to users with visual impairments and may announce the raw image URL."
                    ),
                    suggested_fix='Add a descriptive alt attribute, e.g. alt="Description of image", or alt="" if decorative.',
                    before_html=snippet,
                    after_html="",
                )
            )
    return violations


# =========================================================================
# Rule 2: Missing Form Input Labels [WCAG-1.3.1] (Deterministic)
# =========================================================================
def audit_missing_form_labels(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    excluded_types = {"hidden", "submit", "reset", "button", "image"}
    controls = soup.find_all(["input", "select", "textarea"])

    for ctrl in controls:
        if ctrl.find_parent("template"):
            continue
        if ctrl.name == "input" and ctrl.get("type", "text").lower() in excluded_types:
            continue

        ctrl_id = ctrl.get("id", "")
        has_label = False

        if ctrl_id:
            matching = soup.find("label", attrs={"for": ctrl_id})
            if matching and matching.get_text(strip=True):
                has_label = True

        if not has_label:
            parent_label = ctrl.find_parent("label")
            if parent_label and parent_label.get_text(strip=True):
                has_label = True

        if not has_label:
            aria_label = ctrl.get("aria-label", "").strip()
            if aria_label:
                has_label = True

        if not has_label:
            aria_labelledby = ctrl.get("aria-labelledby", "").strip()
            if aria_labelledby:
                target = soup.find(id=aria_labelledby)
                if target and target.get_text(strip=True):
                    has_label = True

        if not has_label:
            selector = generate_css_selector(ctrl)
            snippet = _clean_snippet(ctrl)
            placeholder = ctrl.get("placeholder", "")
            explanation = (
                f"Form control <{ctrl.name}> lacks an accessible programmatic label (<label for='...'>, wrapping label, or aria-label). "
            )
            if placeholder:
                explanation += (
                    f"Relying solely on placeholder='{placeholder}' violates WCAG 3.3.2 because placeholders "
                    "disappear on user input and are not reliably announced by all screen readers."
                )
            else:
                explanation += "Assistive technologies cannot announce the purpose or required format of this input."

            violations.append(
                Violation(
                    rule_id="WCAG-1.3.1",
                    rule_name="Missing Form Input Label",
                    severity=Severity.CRITICAL,
                    dom_selector=selector,
                    raw_html_snippet=snippet,
                    issue_explanation=explanation,
                    suggested_fix=f'<label for="{ctrl_id or "input-id"}">Field Label</label> or aria-label="Field Label"',
                    before_html=snippet,
                    after_html="",
                )
            )
    return violations


# =========================================================================
# Rule 3: Computed Color Contrast [WCAG-1.4.3] (Deterministic Runtime)
# =========================================================================
def audit_computed_color_contrast(inspection: PageInspectionResult) -> List[Violation]:
    violations: List[Violation] = []
    seen_selectors = set()

    for selector, elem_data in inspection.elements.items():
        if selector in seen_selectors:
            continue

        tag = elem_data.tag_name
        # Evaluate elements bearing text or actionable UI
        if tag not in ["button", "a", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6", "label", "input"]:
            continue

        text = elem_data.text_content.strip()
        if not text and tag != "input":
            continue

        styles = elem_data.styles

        # Filter out elements that are visually hidden or zero-dimensioned
        if (
            not getattr(elem_data, "is_visible", True)
            or styles.get("display") == "none"
            or styles.get("visibility") in ["hidden", "collapse"]
            or styles.get("opacity") == "0"
            or elem_data.attributes.get("aria-hidden") == "true"
            or elem_data.bounding_box.width <= 0
            or elem_data.bounding_box.height <= 0
        ):
            continue

        fg_color = styles.get("color", "")
        bg_color = styles.get("backgroundColor", "")

        if not fg_color or not bg_color:
            continue

        # Check font size / boldness
        font_size_str = styles.get("fontSize", "16px")
        font_weight_str = styles.get("fontWeight", "400")

        is_large = False
        size_match = re.search(r"([\d\.]+)", font_size_str)
        if size_match:
            px_val = float(size_match.group(1))
            is_bold = font_weight_str in ["700", "800", "900", "bold"]
            if px_val >= 24.0 or (px_val >= 18.66 and is_bold):
                is_large = True

        compliant, ratio, threshold = is_contrast_compliant(fg_color, bg_color, is_large_text=is_large)

        if not compliant and ratio < threshold:
            seen_selectors.add(selector)
            violations.append(
                Violation(
                    rule_id="WCAG-1.4.3",
                    rule_name="Insufficient Color Contrast Ratio",
                    severity=Severity.SERIOUS,
                    dom_selector=selector,
                    raw_html_snippet=elem_data.raw_html,
                    issue_explanation=(
                        f"Computed contrast ratio is {ratio}:1, failing WCAG AA threshold of {threshold}:1 "
                        f"(computed foreground '{fg_color}' on background '{bg_color}'). "
                        "Users with low vision or color blindness cannot comfortably perceive this text."
                    ),
                    suggested_fix=f"Adjust text or background color to satisfy minimum {threshold}:1 contrast ratio.",
                    before_html=elem_data.raw_html,
                    after_html="",
                )
            )

    return violations


# =========================================================================
# Rule 4: Heading Order Skips [WCAG-1.3.1H] (Deterministic)
# =========================================================================
def audit_heading_order_skips(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    headings = soup.find_all(re.compile(r"^h[1-6]$"))

    last_level = 0
    for h in headings:
        level = int(h.name[1])
        if last_level > 0 and level > last_level + 1:
            selector = generate_css_selector(h)
            snippet = _clean_snippet(h)
            violations.append(
                Violation(
                    rule_id="WCAG-1.3.1H",
                    rule_name="Heading Hierarchy Skip",
                    severity=Severity.MODERATE,
                    dom_selector=selector,
                    raw_html_snippet=snippet,
                    issue_explanation=(
                        f"Heading structure jumps from <h{last_level}> directly to <h{level}>, skipping <h{last_level+1}>. "
                        "Skipping heading levels creates a disjointed outline in screen reader navigation palettes."
                    ),
                    suggested_fix=f"Change <{h.name}> to <h{last_level+1}> or restructure document sections.",
                    before_html=snippet,
                    after_html="",
                )
            )
        last_level = level

    return violations


# =========================================================================
# Rule 5: Missing Document Language [WCAG-3.1.1] (Deterministic)
# =========================================================================
def audit_document_language(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    html_tag = soup.find("html")

    if not html_tag or not html_tag.has_attr("lang") or not html_tag.get("lang", "").strip():
        snippet = "<html>" if not html_tag else str(html_tag)[:60] + "..."
        violations.append(
            Violation(
                rule_id="WCAG-3.1.1",
                rule_name="Missing Document Language Attribute",
                severity=Severity.SERIOUS,
                dom_selector="html",
                raw_html_snippet=snippet,
                issue_explanation=(
                    "The root <html> element is missing a valid 'lang' attribute. Text-to-speech synthesizers "
                    "cannot determine the appropriate pronunciation rules or Braille translation table."
                ),
                suggested_fix='Add a valid BCP 47 language code to the root element, e.g. <html lang="en">.',
                before_html=snippet,
                after_html='<html lang="en">',
            )
        )
    return violations


# =========================================================================
# Rule 6: Invalid ARIA / Non-focusable Interactive Roles [WCAG-4.1.2] (Deterministic)
# =========================================================================
def audit_interactive_roles_and_aria(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []

    # 1. Custom interactive roles on non-interactive elements without tabindex
    interactive_roles = {"button", "link", "checkbox", "tab", "menuitem"}
    for el in soup.find_all(attrs={"role": True}):
        if el.find_parent("template"):
            continue
        role = el.get("role", "").lower()
        if role in interactive_roles and el.name in ["div", "span", "p", "a", "i", "section"]:
            if not el.has_attr("tabindex"):
                selector = generate_css_selector(el)
                snippet = _clean_snippet(el)
                violations.append(
                    Violation(
                        rule_id="WCAG-4.1.2",
                        rule_name="Non-Focusable Interactive Element",
                        severity=Severity.CRITICAL,
                        dom_selector=selector,
                        raw_html_snippet=snippet,
                        issue_explanation=(
                            f"Element <{el.name} role='{role}'> specifies an interactive role but lacks tabindex='0'. "
                            "Keyboard-only users cannot tab to or activate this custom element."
                        ),
                        suggested_fix=f'Replace with native <{role}> or add tabindex="0" and keyboard activation handlers (Enter/Space).',
                        before_html=snippet,
                        after_html="",
                    )
                )

    # 2. Empty icon-only buttons without accessible name
    for btn in soup.find_all("button"):
        if btn.find_parent("template"):
            continue
        text = btn.get_text(strip=True)
        aria_label = btn.get("aria-label", "").strip()
        aria_labelledby = btn.get("aria-labelledby", "").strip()
        title_attr = btn.get("title", "").strip()
        img = btn.find("img")
        has_img_alt = img and bool(img.get("alt", "").strip())
        svg = btn.find("svg")
        has_svg_title = bool(svg and svg.find("title") and svg.find("title").get_text(strip=True))
        has_svg_aria = bool(svg and (svg.get("aria-label", "").strip() or svg.get("aria-labelledby", "").strip()))

        if not text and not aria_label and not aria_labelledby and not title_attr and not has_img_alt and not has_svg_title and not has_svg_aria:
            selector = generate_css_selector(btn)
            snippet = _clean_snippet(btn)
            violations.append(
                Violation(
                    rule_id="WCAG-4.1.2",
                    rule_name="Button Missing Accessible Name",
                    severity=Severity.CRITICAL,
                    dom_selector=selector,
                    raw_html_snippet=snippet,
                    issue_explanation=(
                        "The <button> contains no readable text, aria-label, title, or accessible image/svg alt/title. "
                        "Screen readers will announce an unlabelled button, preventing users from understanding its action."
                    ),
                    suggested_fix='Add aria-label="Action Name" or include descriptive text.',
                    before_html=snippet,
                    after_html="",
                )
            )

    return violations


# =========================================================================
# Rule 7: Generic Alt Text Quality [WCAG-AI-1.1.1Q] (AI / Heuristic)
# =========================================================================
def audit_generic_alt_text_quality(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    generic_patterns = {
        "image", "photo", "pic", "picture", "icon", "graphic", "logo",
        "placeholder", "untitled", "img", "thumbnail", "banner"
    }

    for img in soup.find_all("img"):
        if img.find_parent("template"):
            continue
        if img.has_attr("alt"):
            alt_val = img.get("alt", "").strip().lower()
            # If alt is present, but matches a generic term or raw filename
            is_generic = (alt_val in generic_patterns) or bool(re.search(r"^(img_\d+|dsc_\d+|screenshot|image|\w+\.(png|jpe?g|svg|webp|gif))$", alt_val))
            if is_generic:
                selector = generate_css_selector(img)
                snippet = _clean_snippet(img)
                violations.append(
                    Violation(
                        rule_id="WCAG-AI-1.1.1Q",
                        rule_name="Non-Descriptive Generic Alt Text",
                        severity=Severity.MODERATE,
                        dom_selector=selector,
                        raw_html_snippet=snippet,
                        issue_explanation=(
                            f"Image alt text '{img.get('alt')}' is uninformative and generic. "
                            "Screen reader users receive no meaningful context regarding the image's content or purpose."
                        ),
                        suggested_fix="Replace with descriptive alt text derived from context or product title.",
                        before_html=snippet,
                        after_html="",
                    )
                )
    return violations


# =========================================================================
# Rule 8: Ambiguous Link & Button Context [WCAG-AI-2.4.4] (AI / Heuristic)
# =========================================================================
def audit_ambiguous_links_and_buttons(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    vague_phrases = {"click here", "read more", "learn more", "more details", "here", "more", "details", "download"}

    for el in soup.find_all(["a", "button"]):
        if el.find_parent("template"):
            continue
        # If element provides unambiguous contextual accessible name via aria-label or aria-labelledby, it is compliant
        aria_label = el.get("aria-label", "").strip()
        if aria_label and aria_label.lower() not in vague_phrases:
            continue
        aria_labelledby = el.get("aria-labelledby", "").strip()
        if aria_labelledby:
            target = soup.find(id=aria_labelledby)
            if target and target.get_text(strip=True).lower() not in vague_phrases:
                continue

        text = el.get_text(strip=True).lower()
        if text in vague_phrases:
            selector = generate_css_selector(el)
            snippet = _clean_snippet(el)
            violations.append(
                Violation(
                    rule_id="WCAG-AI-2.4.4",
                    rule_name="Ambiguous Link/Button Context",
                    severity=Severity.MODERATE,
                    dom_selector=selector,
                    raw_html_snippet=snippet,
                    issue_explanation=(
                        f"Interactive element contains ambiguous text '{el.get_text(strip=True)}'. "
                        "When navigating out of context (e.g. in screen reader link lists), users cannot determine destination or intent."
                    ),
                    suggested_fix='Replace link text with self-describing destination or add informative aria-label.',
                    before_html=snippet,
                    after_html="",
                )
            )
    return violations


# =========================================================================
# Rule 9: Keyboard Focus Trap & Tab-Order Simulation [WCAG-AI-2.1.2] (AI / Heuristic)
# =========================================================================
def audit_keyboard_focus_and_tab_order(inspection: PageInspectionResult) -> List[Violation]:
    violations: List[Violation] = []
    soup = inspection.soup

    # 1. Positive tabindex disrupts sequential focus order (WCAG 2.4.3)
    for el in soup.find_all(attrs={"tabindex": True}):
        try:
            val = int(el.get("tabindex"))
            if val > 0:
                selector = generate_css_selector(el)
                snippet = _clean_snippet(el)
                violations.append(
                    Violation(
                        rule_id="WCAG-AI-2.1.2",
                        rule_name="Disruptive Positive Tabindex",
                        severity=Severity.SERIOUS,
                        dom_selector=selector,
                        raw_html_snippet=snippet,
                        issue_explanation=(
                            f"Element specifies positive tabindex='{val}'. Positive tabindex forces an unnatural "
                            "focus sequence, bypassing preceding interactive elements for keyboard navigators."
                        ),
                        suggested_fix='Use tabindex="0" to preserve natural DOM order or restructure HTML hierarchy.',
                        before_html=snippet,
                        after_html="",
                    )
                )
        except ValueError:
            pass

    # 2. Suppressed focus outlines without replacement
    if re.search(r":focus\s*\{[^}]*outline\s*:\s*none", inspection.html_content, re.IGNORECASE):
        violations.append(
            Violation(
                rule_id="WCAG-AI-2.1.2",
                rule_name="Focus Outline Suppressed",
                severity=Severity.SERIOUS,
                dom_selector="head > style",
                raw_html_snippet="outline: none !important;",
                issue_explanation=(
                    "CSS suppresses default keyboard focus outlines (:focus { outline: none; }) without providing "
                    "a high-contrast replacement focus indicator. Sighted keyboard navigators lose track of active focus."
                ),
                suggested_fix="Ensure interactive elements retain a high-contrast focus ring, e.g. :focus-visible { outline: 3px solid #2563eb; }.",
                before_html="a:focus, button:focus { outline: none !important; }",
                after_html="a:focus-visible, button:focus-visible { outline: 3px solid #2563eb; outline-offset: 2px; }",
            )
        )

    # 3. Interactive elements unreachable during Playwright simulated tab sequence
    for unreach in inspection.unreachable_interactive:
        # Check if already flagged under ARIA non-focusable
        if any(unreach in v.dom_selector for v in violations):
            continue
        # Find element in soup
        target_el = soup.select_one(unreach) if (unreach.startswith("#") or unreach.startswith(".")) else None
        if target_el:
            selector = generate_css_selector(target_el)
            snippet = _clean_snippet(target_el)
            violations.append(
                Violation(
                    rule_id="WCAG-AI-2.1.2",
                    rule_name="Interactive Element Unreachable via Keyboard",
                    severity=Severity.SERIOUS,
                    dom_selector=selector,
                    raw_html_snippet=snippet,
                    issue_explanation=(
                        f"Interactive control '{unreach}' was not reachable during simulated keyboard Tab traversal. "
                        "Keyboard-dependent users cannot access or activate this function."
                    ),
                    suggested_fix='Ensure element is in DOM tab sequence (tabindex="0") and not suppressed by CSS pointer-events.',
                    before_html=snippet,
                    after_html="",
                )
            )

    return violations


# =========================================================================
# Rule 10: Missing Semantic Landmarks [WCAG-AI-1.3.1L] (AI / Heuristic)
# =========================================================================
def audit_semantic_landmarks(soup: BeautifulSoup) -> List[Violation]:
    violations: List[Violation] = []
    
    body = soup.find("body") or soup
    body_text = body.get_text(strip=True) if hasattr(body, "get_text") else ""
    child_tags = [c for c in getattr(body, "children", []) if isinstance(c, Tag)]
    # If the document or body is completely empty (no text and no tag elements), skip landmark checks
    if not body_text and not child_tags:
        return violations

    # Check for primary <main> landmark
    main_landmark = soup.find(["main", "div"], attrs={"role": "main"})
    if not main_landmark and soup.find("main") is None:
        # Document lacks a <main> landmark
        body = soup.find("body") or soup
        body_child = body.find(["div", "section", "article"]) or body
        selector = generate_css_selector(body_child)
        snippet = _clean_snippet(body_child)
        violations.append(
            Violation(
                rule_id="WCAG-AI-1.3.1L",
                rule_name="Missing Primary <main> Landmark",
                severity=Severity.MODERATE,
                dom_selector=selector,
                raw_html_snippet=snippet,
                issue_explanation=(
                    "The document lacks a primary <main> landmark region. Assistive technologies use landmarks "
                    "to allow users to jump directly to primary content, bypassing header navigation."
                ),
                suggested_fix="Wrap primary page content inside a semantic <main> tag or specify role='main'.",
                before_html=snippet,
                after_html=f"<main>\n  {snippet}\n</main>",
            )
        )

    # Check for orphan interactive forms placed outside any landmark
    landmarks = {"header", "nav", "main", "footer", "aside", "section", "article"}
    for form in soup.find_all("form"):
        # Traverse parent chain
        cur = form.parent
        in_landmark = False
        while cur and cur.name and cur.name != "[document]":
            if cur.name in landmarks or cur.get("role") in ["main", "form", "search", "region"]:
                in_landmark = True
                break
            cur = cur.parent

        if not in_landmark:
            selector = generate_css_selector(form)
            snippet = _clean_snippet(form)
            violations.append(
                Violation(
                    rule_id="WCAG-AI-1.3.1L",
                    rule_name="Interactive Form Outside Semantic Landmark",
                    severity=Severity.MODERATE,
                    dom_selector=selector,
                    raw_html_snippet=snippet,
                    issue_explanation=(
                        "Form is situated outside of any landmark region (<main>, <header>, <nav>, <footer>). "
                        "Assistive tools cannot locate or announce this form in the document landmark hierarchy."
                    ),
                    suggested_fix="Enclose form inside <main> or specify role='form' with an accessible name.",
                    before_html=snippet,
                    after_html=f'<section aria-label="Form Region">\n  {snippet}\n</section>',
                )
            )

    return violations


# =========================================================================
# Complete 10-Rule Orchestrator
# =========================================================================
def audit_page_file(file_path: Path | str) -> PageAuditResult:
    """
    Executes all 10 WCAG 2.1 AA audit checks on an HTML file on disk
    using Playwright runtime computed styles, bounding boxes, and DOM parsing.
    """
    path = Path(file_path).resolve()
    inspection = PlaywrightDOMInspector.inspect(path)
    soup = inspection.soup

    all_violations: List[Violation] = []

    # 6 Deterministic Rules
    all_violations.extend(audit_missing_image_alt(soup))               # Rule 1: WCAG-1.1.1
    all_violations.extend(audit_missing_form_labels(soup))             # Rule 2: WCAG-1.3.1
    all_violations.extend(audit_computed_color_contrast(inspection))   # Rule 3: WCAG-1.4.3
    all_violations.extend(audit_heading_order_skips(soup))             # Rule 4: WCAG-1.3.1H
    all_violations.extend(audit_document_language(soup))               # Rule 5: WCAG-3.1.1
    all_violations.extend(audit_interactive_roles_and_aria(soup))       # Rule 6: WCAG-4.1.2

    # 4 AI / Heuristic-Assisted Rules
    all_violations.extend(audit_generic_alt_text_quality(soup))        # Rule 7: WCAG-AI-1.1.1Q
    all_violations.extend(audit_ambiguous_links_and_buttons(soup))     # Rule 8: WCAG-AI-2.4.4
    all_violations.extend(audit_keyboard_focus_and_tab_order(inspection)) # Rule 9: WCAG-AI-2.1.2
    all_violations.extend(audit_semantic_landmarks(soup))              # Rule 10: WCAG-AI-1.3.1L

    # Populate contextual remediations (Before / After code snippets)
    from auditor.llm_remediator import LLMRemediator
    remediator = LLMRemediator()
    remediator.enrich_violations_with_remediation(all_violations, soup)

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
        page_name=path.name,
        file_path=str(path),
        total_violations=len(all_violations),
        violations_by_severity=by_severity,
        violations=all_violations,
        status=status,
    )
