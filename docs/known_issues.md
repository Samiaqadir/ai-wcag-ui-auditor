# Known Issues & Technical Limitations Log

**Project:** AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor  
**Engine Version:** 2.4.0  
**Last Updated:** November 2026  
**Status:** Active Reference & Engineering Roadmap

---

## Executive Overview
The AI Accessibility & UI Regression Auditor leverages a hybrid architecture combining Playwright Chromium runtime inspection, computed style analysis (`window.getComputedStyle`), DOM tree parsing (BeautifulSoup4 / lxml), and LLM-assisted context remediation.

While deterministic and highly accurate for standard SSR, static, and client-rendered HTML5 web documents, specific architectural constraints and security boundaries inherent to modern web browsers introduce limitations. This document records all known technical limitations, architectural edge cases, and mitigation strategies.

---

## 1. Dynamic JavaScript Single Page Applications (SPA) & Virtual DOM

### 1.1 Virtual DOM Hydration Latency & Dynamic Route Transitions
* **Limitation:** In client-side single page frameworks (React, Vue, Angular, Next.js client components, Svelte), DOM subtrees are mounted asynchronously after initial HTML parsing. If an audit triggers before client-side hydration or network fetch completion, newly rendered components may be omitted from the audit snapshot.
* **Impact:** Modal overlays, notification toasts, or client-side conditional views (e.g. `v-if`, `{isOpen && <Modal />}`) that depend on user interactions or delayed async state will only be evaluated in their default initial render state.
* **Mitigation / Workaround:**
  - Configure page load wait conditions: use `page.goto(url, wait_until="networkidle")` or wait for specific root selectors (`page.wait_for_selector("#app-root")`).
  - For complex SPAs, inject interaction scripts or use Playwright user journey recordings before triggering the auditor.

### 1.2 Web Components with Closed Shadow DOM
* **Limitation:** Web Components initialized with closed shadow roots (`element.attachShadow({ mode: 'closed' })`) strictly encapsulate their internal DOM hierarchy.
* **Impact:** Standard recursive selectors (`document.querySelectorAll('*')`) cannot pierce closed shadow root boundaries. The auditor evaluates the host custom element (`<my-component>`), but cannot inspect child buttons, inputs, or text nodes inside closed shadow trees.
* **Mitigation / Workaround:**
  - Standard enterprise component libraries should maintain open shadow roots (`mode: 'open'`) during QA/staging test builds to permit accessibility tooling introspection.
  - Evaluate components at unit level before shadow encapsulation.

---

## 2. Browser Security & Sandbox Boundaries

### 2.1 Cross-Origin `<iframe>` Isolation
* **Limitation:** The W3C Same-Origin Policy (SOP) prohibits scripts running in the parent frame from accessing the DOM, CSS styles, or bounding boxes of child frames hosted on different origins or protocols (e.g., Stripe payment iframes, reCAPTCHA widgets, YouTube embeds).
* **Impact:** Cross-origin iframe contents are inaccessible to in-page JavaScript extraction scripts (`SecurityError: Blocked a frame with origin from accessing a cross-origin frame`).
* **Mitigation / Workaround:**
  - The auditor validates the `<iframe>` container element itself (ensuring it contains an informative `title` attribute per WCAG 2.4.1 / 4.1.2).
  - Child iframes should be audited independently by pointing the auditor directly to their source URI.

### 2.2 System Audio & Native Video Tracks
* **Limitation:** The auditor inspects `<video>` and `<audio>` tags for accessible captions (`<track kind="captions">`) and alternative text, but cannot synthesize speech-to-text or decode closed caption streams in real time.
* **Impact:** Verification of caption accuracy or audio description synchronization requires external multimodal model integration.

---

## 3. Graphical Rendering & Visual Layout Edge Cases

### 3.1 HTML5 `<canvas>` and WebGL Contexts
* **Limitation:** Elements drawn on an HTML5 `<canvas>` or rendered via WebGL (3D graphics, charting libraries like Chart.js or Three.js) are rendered as raw raster bitmap pixels.
* **Impact:** The browser accessibility tree cannot detect individual shapes, text labels, or contrast inside canvas buffers. `window.getComputedStyle` only reports the styling of the `<canvas>` wrapper.
* **Mitigation / Workaround:**
  - Ensure canvas elements provide a semantic fallback DOM subtree inside `<canvas>...</canvas>` or use ARIA attributes (`role="img"`, `aria-label="..."`).
  - Visual layout regression diffing (`auditor/regression.py`) detects canvas dimension shifts, but semantic text checks require OCR.

### 3.2 Complex CSS Gradients, Blend Modes, and Background Images
* **Limitation:** The color contrast engine computes contrast against the nearest solid ancestor background color (`backgroundColor`). When text is superimposed on multi-stop CSS gradients (`linear-gradient(...)`), CSS blend modes (`mix-blend-mode`), or photographic background images (`background-image: url(...)`), exact per-pixel luminosity varies across characters.
* **Impact:** The calculated contrast ratio represents the background base color rather than local pixel luminance.
* **Mitigation / Workaround:**
  - Web authors should provide solid contrast backing plates (e.g. `background-color: rgba(0,0,0,0.7)`) behind text overlaid on imagery.
  - Future iterations will introduce canvas screenshot pixel-sampling under text bounding boxes.

### 3.3 Dynamic CSS Transitions and Active Animations
* **Limitation:** If a page is audited while CSS transition animations (e.g. `fade-in`, `slide-down`) are actively executing, computed opacity or position coordinates may be captured midway (e.g. `opacity: 0.35` instead of `1.0`).
* **Impact:** Potential transient contrast failures or bounding box shifts during rapid state changes.
* **Mitigation / Workaround:**
  - The Playwright DOM inspector automatically injects reduced motion headers (`page.emulate_media(reduced_motion="reduce")`) to freeze animations.
  - Ensure animations are completed before calling `PlaywrightDOMInspector.inspect()`.

---

## 4. Parser & Heuristic Boundary Specifications

### 4.1 Zero-Dimension / Offscreen Elements
* **Engine Rule:** Elements styled with `display: none`, `visibility: hidden`, `opacity: 0`, or bearing `aria-hidden="true"` with zero bounding dimensions are intentionally excluded from color contrast evaluation to prevent false-positive defects on hidden UI states.
* **Known Boundary:** Elements positioned offscreen via large negative margins (e.g. `left: -9999px`) for screen-reader-only utility classes (e.g. `.sr-only`) may fail contrast if text color matches background, unless styled with standard clipping patterns (`clip: rect(0,0,0,0)`).

### 4.2 Adversarial Prompt Injection Defense
* **Engine Rule:** All raw DOM content, element text, comments, and attribute strings are defanged via `sanitize_untrusted_input()` and validated via `validate_remediation_output()`.
* **Known Boundary:** Obfuscated Unicode homoglyph injection patterns are defanged by the heuristic pattern set, but production enterprise deployments must combine this with rate-limiting and model system instructions.

---

## 5. Engineering Roadmap & Upcoming Mitigations

| Target Milestone | Enhancement Area | Technical Solution |
| :--- | :--- | :--- |
| **v2.5** | Canvas & Image Contrast | Implement headless Chromium screenshot cropping + PIL pixel-luminance histogram analysis. |
| **v2.6** | SPA Dynamic Traversal | Playwright automated state crawler traversing tabs, modals, and dropdown disclosure widgets. |
| **v2.7** | Open Shadow DOM Piercing | Enhanced recursive CSS selector generator supporting `>>>` deep shadow DOM combinators. |
| **v2.8** | Cross-Origin Iframe Proxy | Sandboxed child-frame evaluator for whitelisted staging domains. |
