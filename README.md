# AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor

[![WCAG 2.1 AA Compliant](https://img.shields.io/badge/WCAG%202.1-Level%20AA-blue.svg)](https://www.w3.org/TR/WCAG21/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Playwright Chromium](https://img.shields.io/badge/Playwright-Chromium%20Runtime-green.svg)](https://playwright.dev/python/)
[![Streamlit UI](https://img.shields.io/badge/Streamlit-Interactive%20QA%20Dashboard-FF4B4B.svg)](https://streamlit.io/)
[![12-Case Regression](https://img.shields.io/badge/Regression%20Suite-12%2F12%20PASS-brightgreen.svg)]()
[![Zero False-Positive Criticals](https://img.shields.io/badge/Compliant%20Pages-0%20False%20Positives-brightgreen.svg)]()

An enterprise-grade accessibility compliance and visual UI regression auditing platform. Built with **Playwright headless Chromium runtime inspection**, **deterministic CSS computed style/geometry analysis**, **context-aware LLM HTML/ARIA code remediation with adversarial prompt injection defenses**, and an **interactive Streamlit QA Triage Dashboard**.

---

## Table of Contents
- [Executive Overview](#executive-overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Supported WCAG 2.1 AA Ruleset](#supported-wcag-21-aa-ruleset)
- [Project Directory Structure](#project-directory-structure)
- [Installation & Quickstart](#installation--quickstart)
- [Usage Guide](#usage-guide)
  - [1. Interactive QA Dashboard (Web UI)](#1-interactive-qa-dashboard-web-ui)
  - [2. CLI Automated Audit Suite](#2-cli-automated-audit-suite)
  - [3. Running the 12-Case Regression Suite](#3-running-the-12-case-regression-suite)
  - [4. Security Injection & Report Validation Tests](#4-security-injection--report-validation-tests)
- [Human QA Triage Workflow](#human-qa-triage-workflow)
- [Multi-Format Report Export](#multi-format-report-export)
- [Known Limitations & Roadmap](#known-limitations--roadmap)
- [License & Contributions](#license--contributions)

---

## Executive Overview
Modern web applications frequently suffer from accessibility regressions, contrast violations, and broken keyboard navigation introduced during rapid sprint cycles. Traditional linters only inspect static HTML strings and miss computed CSS colors, dynamic layout shifts, and element visibility states.

The **AI Accessibility & UI Regression Auditor** bridges this gap:
1. **Renders pages in real headless Chromium** via Playwright to extract live computed styles (`window.getComputedStyle`) and bounding boxes (`getBoundingClientRect()`).
2. **Evaluates 10 WCAG 2.1 AA rules** (6 deterministic runtime rules + 4 AI/heuristic rules) with guaranteed verifiable CSS DOM selectors.
3. **Generates drop-in accessible code fixes** using Google GenAI or context-aware heuristic AST patchers.
4. **Defends against adversarial prompt injection attacks** embedded inside untrusted HTML comments or attributes.
5. **Compares baseline vs modified snapshots** to detect visual layout shifts, style regressions, and DOM tree mutations.
6. **Empowers QA Leads** with an interactive Streamlit triage dashboard that recalculates compliance scores in real-time as issues are reviewed.

---

## Key Features

- **Runtime Computed Contrast:** Evaluates real sRGB luminance for foreground and background colors (thresholds: 4.5:1 for normal text, 3.0:1 for large text). Automatically filters out visually hidden nodes (`display: none`, `visibility: hidden`, `opacity: 0`, `aria-hidden="true"`, or zero-sized bounding boxes).
- **Simulated Keyboard Tab Navigation:** Simulates real `Tab` key traversal via Playwright to uncover keyboard focus traps, unreachable controls, and disruptive positive `tabindex` attributes.
- **Context-Aware Remediation:** Produces drop-in Before & After HTML/ARIA replacements enriched with parent and sibling DOM context.
- **Adversarial Prompt Injection Defense:** Defangs malicious prompts embedded in HTML comments, `alt` text, or placeholders (`sanitize_untrusted_input`) and quarantines unsafe responses (`validate_remediation_output`).
- **Visual Layout & DOM Regression Diffing:** Compares geometric coordinates $(x, y, w, h)$, computed CSS properties, and DOM structural mutations between revisions.
- **Interactive Triage & Live Scoring:** Review findings, assign statuses (`Confirmed Defect`, `False Positive`, `Won't Fix`), record reviewer notes, and watch the WCAG compliance score dynamically recalculate.
- **Multi-Format Export:** Generates self-contained print-ready HTML reports, GitHub/Jira-formatted Markdown tables, and RFC 4180 CSV spreadsheets.

---

## System Architecture

```mermaid
flowchart TD
    HTML[Target HTML Page / URL] --> PW[Playwright Headless Chromium]
    PW --> Inspector[PlaywrightDOMInspector\n- Computed CSS Styles\n- Bounding Boxes (x, y, w, h)\n- Simulated Tab Traversal]
    PW --> Soup[BeautifulSoup4 / lxml DOM Tree]
    
    Inspector & Soup --> Engine[10-Rule WCAG 2.1 AA Engine]
    
    subgraph Engine[Auditor Engine: rules.py]
        R1[WCAG-1.1.1 Missing Image Alt]
        R2[WCAG-1.3.1 Missing Form Labels]
        R3[WCAG-1.4.3 Computed Color Contrast]
        R4[WCAG-1.3.1H Heading Hierarchy Skips]
        R5[WCAG-3.1.1 Missing Document Lang]
        R6[WCAG-4.1.2 Invalid ARIA / Roles]
        R7[WCAG-AI-1.1.1Q Generic Alt Quality]
        R8[WCAG-AI-2.4.4 Ambiguous Link/Button]
        R9[WCAG-AI-2.1.2 Tab Order & Focus Traps]
        R10[WCAG-AI-1.3.1L Semantic Landmarks]
    end
    
    Engine --> Violations[Flagged Violations List]
    Violations --> Remediation[Context-Aware LLM Remediation\n- Prompt Injection Sanitization\n- GenAI SDK / Heuristic AST Fallback\n- Output Validation & Quarantine]
    
    Baseline[Baseline Snapshot] & Modified[Modified Snapshot] --> Regression[Regression Diff Engine: regression.py\n- Layout Shifts Δx, Δy, Δw, Δh\n- Computed Style Regressions\n- Structural DOM Mutations]
    
    Remediation & Regression --> Dashboard[Streamlit Interactive QA Dashboard: app.py]
    Dashboard --> Triage[QA Triage Controls\n- Dynamic Compliance Score\n- Status Badges & Reviewer Notes]
    Triage --> Exporter[Multi-Format Exporter: exporter.py]
    Exporter --> Reports[HTML / Markdown / CSV Reports]
```

---

## Supported WCAG 2.1 AA Ruleset

| Rule ID | Rule Name | Category | WCAG Criterion | Default Severity | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`WCAG-1.1.1`** | Missing Image Alternative Text | Deterministic | 1.1.1 (Level A) | `Critical` | Flags `<img>` tags completely missing an `alt` attribute. Decorative elements must have explicit `alt=""` or `role="presentation"`. |
| **`WCAG-1.3.1`** | Missing Form Input Label | Deterministic | 1.3.1 / 3.3.2 (Level A) | `Critical` | Flags form inputs (`<input>`, `<select>`, `<textarea>`) lacking matching `<label for="...">`, wrapping `<label>`, or `aria-label`. |
| **`WCAG-1.4.3`** | Insufficient Color Contrast | Deterministic | 1.4.3 (Level AA) | `Serious` | Computes relative luminance ratio ($CR$). Fails if $CR < 4.5:1$ (normal text) or $CR < 3.0:1$ (large text $\ge$ 24px or $\ge$ 18.66px bold). |
| **`WCAG-1.3.1H`** | Heading Hierarchy Skips | Deterministic | 1.3.1 (Level A) | `Moderate` | Flags non-sequential heading progressions (e.g. `<h1>` followed directly by `<h4>`, skipping `<h2>` and `<h3>`). |
| **`WCAG-3.1.1`** | Missing Document Language | Deterministic | 3.1.1 (Level A) | `Serious` | Flags `<html>` root tags lacking a valid BCP 47 `lang` attribute (e.g. `<html lang="en">`). |
| **`WCAG-4.1.2`** | Invalid ARIA / Non-Focusable | Deterministic | 4.1.2 (Level A) | `Critical` | Flags custom interactive roles (`role="button"`) lacking `tabindex="0"`, or empty `<button>` tags without accessible names or SVG titles. |
| **`WCAG-AI-1.1.1Q`** | Generic Alt Text Quality | AI / Heuristic | 1.1.1 (Level A) | `Moderate` | Flags uninformative placeholders such as `"image"`, `"photo"`, `"logo"`, or raw filenames (`"img_0124.png"`). |
| **`WCAG-AI-2.4.4`** | Ambiguous Link/Button Context | AI / Heuristic | 2.4.4 (Level AA) | `Moderate` | Flags vague clickable text (`"Click here"`, `"Read more"`, `"Details"`) that lack descriptive context or `aria-label`. |
| **`WCAG-AI-2.1.2`** | Keyboard Tab Order & Focus Trap | AI / Heuristic | 2.1.2 / 2.4.3 (Level A) | `Serious` | Flags positive `tabindex > 0`, suppressed focus outlines (`:focus { outline: none; }`), or interactive elements skipped during Tab navigation. |
| **`WCAG-AI-1.3.1L`** | Missing Semantic Landmarks | AI / Heuristic | 1.3.1 (Level A) | `Moderate` | Flags documents lacking a primary `<main>` landmark, or interactive forms situated outside of standard landmark regions. |

---

## Project Directory Structure

```text
├── app.py                             # Interactive Streamlit QA Triage Dashboard
├── main.py                            # CLI Entry point & automated audit runner
├── requirements.txt                   # Production dependencies
├── .gitignore                         # Standard git ignore definitions
├── auditor/                           # Core Engine Package
│   ├── __init__.py
│   ├── contrast.py                    # W3C relative luminance & contrast algorithms
│   ├── exporter.py                    # HTML, Markdown, CSV multi-format report exporter
│   ├── llm_remediator.py              # Context-aware patch generator & injection defense
│   ├── models.py                      # Pydantic v2 schemas for violations, triage & diffs
│   ├── parser.py                      # Playwright runtime style extraction & DOM inspector
│   ├── regression.py                  # Geometric layout shift & CSS regression diffing
│   └── rules.py                       # Complete 10-rule WCAG audit engine orchestrator
├── docs/                              # Technical Specifications & Guides
│   ├── audit_rules.md                 # 10 WCAG audit rule specifications
│   ├── demo_script.md                 # 5–7 minute live walkthrough & narration script
│   ├── known_issues.md                # Known issues & dynamic SPA technical limitations
│   └── qa_handover_report.md          # Comprehensive QA Lead handover documentation
├── output/                            # Generated Audit Reports & Verification Evidence
│   ├── 12_case_regression_matrix.json # 12-case regression matrix results
│   ├── audit_01_checkout.json         # E-commerce individual audit findings
│   ├── before_after_fixes.md          # Remediation code showcase
│   ├── initial_audit_report.json      # Comprehensive multi-page JSON report
│   ├── regression_diff_report.json    # Layout shift & DOM mutation diff evidence
│   └── sample_qa_audit_report.html    # Executive styled HTML audit report
├── test_pages/                        # 12-Case Regression Test Pack
│   ├── 01_ecommerce_checkout.html     # Baseline E-commerce checkout (seeded violations)
│   ├── 01_ecommerce_checkout_modified.html # Layout-shifted variant for regression diffing
│   ├── 02_saas_dashboard.html         # SaaS dashboard (heading skips, unlabelled icons)
│   ├── 03_signup_form.html            # Registration form (placeholder labels, bad tabindex)
│   ├── 04_blog_article.html           # Blog post (missing lang, ambiguous links, focus loss)
│   ├── 05_accessible_reference.html   # 100% WCAG AA compliant reference portal
│   ├── 06_malformed_html.html         # Malformed/unclosed tags resilience test
│   ├── 07_empty_body.html             # Empty body edge case (zero-crash verification)
│   ├── 08_inline_svg_graphics.html    # Accessible vs unlabelled inline SVG elements
│   ├── 09_deeply_nested_tables.html   # 4-tier deeply nested layout & data tables
│   ├── 10_already_compliant_portal.html # 100% compliant enterprise HR portal
│   ├── 11_prompt_injection_payloads.html # Adversarial prompt injection payloads
│   └── 12_dynamic_js_edge_cases.html  # Dynamic SPA hidden nodes & template fragments
└── tests/                             # Automated Test Suites
    ├── run_12_regression_suite.py     # 12-case regression suite runner
    ├── test_report_validation.py      # HTML5, RFC 4180 CSV, and patch syntax tests
    └── test_security_injection.py     # Prompt injection and XSS defense tests
```

---

## Installation & Quickstart

### Prerequisites
- **Python 3.10+** (Tested on Python 3.10 through 3.14)
- **Git**
- Optional: Google Gemini API key (for live GenAI remediation; intelligent AST heuristic fallback operates seamlessly without any API key)

### 1. Clone the Repository
```bash
git clone https://github.com/Samiaqadir/ai-wcag-ui-auditor.git
cd ai-wcag-ui-auditor
```

### 2. Set Up Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies & Playwright Browser
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Optional: Configure Gemini API Key
Create a `.env` file in the root directory if you wish to use live Google Gemini LLM remediation:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

---

## Usage Guide

### 1. Interactive QA Dashboard (Web UI)
Launch the Streamlit web dashboard:
```bash
streamlit run app.py
```
Open your browser at **`http://localhost:8501`**.

1. Choose a page from the **Sample Test Pack** dropdown (e.g. `01_ecommerce_checkout.html`).
2. Optionally check **"Enable UI Regression Diffing"** and select a baseline.
3. Click **"⚡ Run WCAG & UI Audit"**.
4. Review KPI cards, filter by severity, examine the **🔴 Before** vs **🟢 After** code diffs, make triage decisions, and export reports.

### 2. CLI Automated Audit Suite
Run the full CLI auditing workflow across sample pages with DOM selector verification and layout regression diffing:
```bash
python main.py
```
Outputs generated:
- `/output/audit_01_checkout.json`
- `/output/regression_diff_report.json`
- `/output/before_after_fixes.md`
- `/output/initial_audit_report.json`

### 3. Running the 12-Case Regression Suite
Run the automated 12-case regression test pack:
```bash
python tests/run_12_regression_suite.py
```
*Expected Outcome:* **12/12 Cases Passed in ~11 seconds** with **0 false-positive criticals** on compliant fixtures (`05_accessible_reference.html`, `07_empty_body.html`, `09_deeply_nested_tables.html`, `10_already_compliant_portal.html`, `12_dynamic_js_edge_cases.html`).

### 4. Security Injection & Report Validation Tests
Run all unit and security defense tests:
```bash
python -m unittest discover tests
```
Validates:
- Neutralization of malicious prompt injections in HTML comments, `alt` tags, and placeholders.
- Stripping of dangerous `<script>` tags, `javascript:` schemes, and `on\w+=` event handlers.
- Validation of exported HTML5 reports, RFC 4180 CSV tables, and balanced HTML syntax of all generated code patches.

---

## Human QA Triage Workflow

Every flagged violation in the platform supports a formal QA review lifecycle:

1. **Pending (Default):** Newly audited finding awaiting human assessment.
2. **Confirmed Defect:** Validated accessibility barrier requiring frontend engineering resolution. Included in compliance penalty calculations.
3. **False Positive:** Element assessed by QA as meeting accessible intent through out-of-band context (e.g., decorative background, screen reader announced elsewhere). **Excluded from compliance score penalty**, dynamically restoring score points.
4. **Won't Fix:** Known product design exception tracked in the sprint backlog.
5. **Reviewer Notes:** Persistent text area allowing the QA engineer to record ticket numbers (e.g. `JIRA-4821`), manual screen reader observations (NVDA/JAWS), or architectural justifications.

---

## Multi-Format Report Export

The exporter engine ([`auditor/exporter.py`](auditor/exporter.py)) supports three standardized enterprise export formats:

1. **Executive Print-Ready HTML Report (`export_to_html`):**
   - Styled executive dashboard with dynamic SVG compliance gauge, KPI summary cards, triage status badges, and styled Before/After diff blocks. Formatted for print or PDF archiving.
2. **GitHub / Jira Markdown Report (`export_to_markdown`):**
   - Ready to paste directly into GitHub PR review comments or Jira tickets with fenced code diff blocks and triage status tables.
3. **Structured CSV Table (`export_to_csv`):**
   - 11-column RFC 4180 compliant CSV export ready for import into Excel, Google Sheets, or bug-tracking pipelines:
     `Page Name`, `Rule ID`, `Rule Name`, `Severity`, `Triage Status`, `Reviewer Notes`, `DOM Selector`, `Issue Explanation`, `Suggested Fix`, `Before HTML`, `After HTML`.

---

## Known Limitations & Roadmap

While deterministic and highly accurate for standard SSR, static, and client-rendered HTML5 pages, specific modern browser sandboxing boundaries apply. See [docs/known_issues.md](docs/known_issues.md) for full technical analysis:

- **Virtual DOM Hydration Latency:** Asynchronously mounted single-page app components (React/Vue/Angular) should be evaluated after `networkidle` or custom selector readiness.
- **Closed Shadow DOM:** Custom elements using `attachShadow({ mode: 'closed' })` cannot be traversed by standard DOM selectors.
- **Cross-Origin `<iframes>`:** Third-party iframes (e.g. Stripe, reCAPTCHA) are protected by browser Same-Origin Policy; container `title` attributes are audited, but internal iframe DOMs must be audited independently.
- **HTML5 `<canvas>` / WebGL Text:** Graphical text rendered on canvas surfaces lacks DOM nodes and requires computer vision / OCR heuristics.
- **Complex CSS Gradients:** Contrast calculations sample the nearest solid background color; future milestones will integrate headless screenshot pixel histogram sampling.

---

## Acceptance Verification for Team Lead Handover

To verify the platform end-of-day acceptance check locally:

```powershell
# 1. Activate environment
.\venv\Scripts\Activate.ps1

# 2. Run automated regression suite (all 12 cases must pass)
python tests/run_12_regression_suite.py

# 3. Launch interactive dashboard
streamlit run app.py
```
- Open `http://localhost:8501`.
- Select `01_ecommerce_checkout.html` and click **"⚡ Run WCAG & UI Audit"**.
- Confirm that **7 violations** are detected with verifiable DOM selectors.
- Mark Violation #2 as **False Positive**; observe the compliance score immediately recalculate.
- Click **"Download HTML Report"** and open the generated report in your browser.

---

**Built with precision by Samia | AI Accessibility & UI QA Automation Lead**  
*Repository:* [https://github.com/Samiaqadir/ai-wcag-ui-auditor](https://github.com/Samiaqadir/ai-wcag-ui-auditor)
