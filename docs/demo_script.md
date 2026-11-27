# 5–7 Minute Live Demo Script & Walkthrough Guide

**Project:** AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor  
**Presenter:** Samia | Senior Full-Stack & QA Automation Lead  
**Target Audience:** QA Engineering Leads, Frontend Architects, Product Managers  
**Total Estimated Runtime:** 6 minutes 15 seconds (bounded within 5–7 minutes)  
**Live UI URL:** `http://localhost:8501`

---

## Demo Schedule & Timeline Overview

| Segment | Timing | Key Objective | UI Action |
| :---: | :---: | :--- | :--- |
| **Part 1** | `0:00 - 1:00` | Platform Orientation & Problem Statement | Introduce Dashboard, KPI headers, and input modes |
| **Part 2** | `1:00 - 2:15` | Load Regression Fixture & Run Live Audit | Select `01_ecommerce_checkout_modified.html` with baseline diff |
| **Part 3** | `2:15 - 3:30` | Inspect Prioritized WCAG Violations | Filter by Severity (`Critical` / `Serious`), review DOM selectors |
| **Part 4** | `3:30 - 4:45` | Review AI-Generated Code Patches & Diffs | Inspect side-by-side Before/After diffs & prompt injection guardrails |
| **Part 5** | `4:45 - 5:30` | QA Triage Decision & Live Score Update | Mark False Positive with notes; observe score recalculation |
| **Part 6** | `5:30 - 6:15` | Multi-Format Report Export & Handover | Download Executive HTML, Markdown, and CSV reports |

---

## Detailed Step-by-Step Script & Narration Cue Sheet

### Part 1: Platform Orientation & Problem Statement (0:00 – 1:00)
* **Presenter UI Action:**
  - Open browser at `http://localhost:8501`.
  - Point to the header banner, KPI metrics area, and the sidebar input controls.
* **Narration Script:**
  > *"Good morning team. Today I am excited to demonstrate our **AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor**.
  > 
  > Traditional accessibility tools often suffer from high false-positive rates because they analyze raw HTML strings rather than how the browser actually renders the page. Our platform solves this by running a real headless Chromium instance via Playwright to extract live computed styles, bounding box coordinates, and real keyboard tab order.
  > 
  > It couples deterministic rule execution with context-aware AI code remediation and visual layout regression diffing. Let's see it in action."*

---

### Part 2: Loading Regression Fixtures & Executing Audit (1:00 – 2:15)
* **Presenter UI Action:**
  - In the left sidebar under **"Select Input Source Mode"**, keep **"Sample Test Pack"** selected.
  - From the dropdown, select: `01_ecommerce_checkout_modified.html`.
  - Toggle the checkbox: **"Enable UI Regression Diffing"**.
  - In the **"Baseline Snapshot"** selector, choose: `01_ecommerce_checkout.html`.
  - Click the primary button: **"⚡ Run WCAG & UI Audit"**.
  - Let the spinner run for 1–2 seconds while Playwright inspects the page.
* **Narration Script:**
  > *"To demonstrate our end-to-end capabilities, I am loading our modified E-commerce checkout page. In this version, our team intentionally introduced both accessibility defects and visual layout shifts compared to our sprint baseline.
  > 
  > Notice I’ve toggled 'Enable UI Regression Diffing' against our baseline checkout snapshot.
  > 
  > Now, I'll click 'Run WCAG & UI Audit'. Under the hood, Playwright launches headless Chromium, computes all element geometry and colors, and simulates a full keyboard Tab traversal."*

---

### Part 3: Inspecting Prioritized WCAG Violations (2:15 – 3:30)
* **Presenter UI Action:**
  - Point out the top **WCAG 2.1 AA Compliance Score Badge** (shows current failing score, e.g. ~42%).
  - Highlight the KPI cards: Total Findings, Confirmed Defects, Critical/Serious, and False Positives.
  - In the **"Filter by Severity"** dropdown, select **"Critical"**.
  - Scroll down to the first card: `WCAG-1.1.1 Missing Image Alternative Text` on selector `#main-cart-item > img`.
  - Scroll to the second card: `WCAG-1.3.1 Missing Form Input Label` on selector `#cc-number`.
  - Switch filter to **"Serious"** and highlight `WCAG-1.4.3 Insufficient Color Contrast` on `#btn-submit-payment`.
* **Narration Script:**
  > *"The audit has completed in under two seconds. Immediately, you see our overall WCAG Compliance Score is at 42%, with 7 distinct violations detected.
  > 
  > Filtering to 'Critical' severity, we see two major blockers:
  > First, our primary product thumbnail lacks an `alt` attribute (`#main-cart-item > img`), meaning screen readers will read a raw cryptic file path.
  > Second, credit card form fields lack associated `<label>` tags, relying solely on placeholder text that disappears upon input.
  > 
  > Notice that every single violation provides an exact, verifiable DOM selector like `#btn-submit-payment` rather than vague line numbers, making debugging trivial for frontend developers."*

---

### Part 4: Reviewing AI-Generated HTML/ARIA Patches & Diffs (3:30 – 4:45)
* **Presenter UI Action:**
  - Scroll to the **2-column Side-by-Side Code Diff View** inside the `WCAG-1.1.1` issue card.
  - Point to the left column: **🔴 Before (Violating Code)**.
  - Point to the right column: **🟢 After (Remediated Code)**.
  - Highlight that the AI remediation extracted the surrounding product title (*"Noise Cancelling Wireless Headphones"*) to generate a meaningful `alt` attribute.
  - Click the **"📋 Copy Remediated Code"** button (shows *Copied to clipboard* confirmation).
  - Scroll down to the Visual Layout Regression panel to show the detected layout shifts (e.g. `#btn-submit-payment` shifted right by 115px).
* **Narration Script:**
  > *"Rather than just reporting errors, the engine generates context-aware, drop-in replacement code.
  > 
  > In this side-by-side diff view on the left, you see the broken HTML. On the right, our LLM remediator didn't just guess—it inspected the surrounding DOM context, identified that this image represents our 'Wireless Noise Cancelling Headphones', and injected a descriptive, semantic `alt` attribute.
  > 
  > Crucially, our engine includes strict adversarial prompt injection defenses. Even if untrusted user content contains malicious override prompts or embedded scripts, our sanitizer neutralizes them before remediation.
  > 
  > A developer can simply click 'Copy Remediated Code' and paste it directly into their pull request."*

---

### Part 5: Human QA Triage & Live Score Recalculation (4:45 – 5:30)
* **Presenter UI Action:**
  - Scroll to Finding #2 (the secondary thumbnail or decorative icon).
  - In the **"Update Triage Status"** dropdown, change the status from `Pending` to **`False Positive`**.
  - In the **"QA Reviewer Notes"** text box, type:
    `Verified with NVDA: Decorative thumbnail; product heading h3 already announces item name to screen reader.`
  - Click **"Save Triage Assessment"**.
  - Point to the top **Compliance Score Gauge**: show that the score has dynamically increased (e.g., from 42% to 54%), and the "False Positives Filtered" KPI updated to 1.
* **Narration Script:**
  > *"Automated tools cannot understand all business context, so we built a robust QA triage loop.
  > 
  > Suppose our QA team reviews Finding #2 and determines with a screen reader that this secondary thumbnail is decorative, because the adjacent `<h3>` heading already announces the product name.
  > 
  > I’ll mark this finding as a **False Positive** and record my QA reviewer notes for the sprint audit trail.
  > 
  > As soon as I save, watch the top compliance score badge—it immediately recalculates to 54%! False positives no longer penalize the team's compliance metrics, giving our engineering organization a truthful reflection of accessible quality."*

---

### Part 6: Multi-Format Report Export & Handover (5:30 – 6:15)
* **Presenter UI Action:**
  - Scroll down to the **"Export & Handover Reports"** section.
  - Click **"📄 Download Executive HTML Report"** and open the downloaded HTML file in a new tab. Show the styled executive KPI cards, triage status badges, and Before/After blocks.
  - Briefly click **"📝 Download Markdown Report"** (ready for GitHub PR comments / Jira).
  - Briefly click **"📊 Download CSV Table"** (ready for Excel / Jira backlog import).
* **Narration Script:**
  > *"Finally, we need to share our audit evidence with leadership and engineering.
  > 
  > We support three export formats with a single click:
  > 1. An **Executive HTML Report**—fully styled, self-contained, and print-ready with all reviewer notes and compliance gauges intact.
  > 2. A **Markdown Summary** formatted for pasting directly into GitHub PR comments.
  > 3. An RFC 4180 **CSV Report** ready for import into Jira or Excel.
  > 
  > The platform is fully automated, deterministic, and ready for team lead handover."*

---

## Demo Checklist for the Presenter

- [x] Streamlit app running on `http://localhost:8501`.
- [x] Chromium Playwright binary installed and operational.
- [x] Test pages folder populated with all 12 regression fixtures and baseline variants.
- [x] Clipboard permissions enabled in browser for the copy buttons.
- [x] Sample HTML report pre-rendered in `/output/sample_qa_audit_report.html` as backup.
- [x] Total demo runtime within target: **5–7 minutes**.
