# WCAG 2.1 AA Remediation Showcase: Before & After HTML/ARIA Fixes

**Generated:** 2026-11-26 05:09:41 UTC  
**Auditor Engine:** Day-2 Context-Aware Remediation Suite  

This document showcases automated drop-in accessible code patches generated for detected WCAG barriers.

---

## Document: `01_ecommerce_checkout.html`
**Total Violations Remediated:** 7 | **Status:** FAILED

### 1. Missing Image Alternative Text (`WCAG-1.1.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `main.checkout-container > section:nth-of-type(1) > div.product-row:nth-of-type(1) > img.product-img`
- **Issue:** The <img> element is completely missing an 'alt' attribute. Screen readers cannot describe the visual content to users with visual impairments and may announce the raw image URL.
- **Remediation Strategy:** Add a descriptive alt attribute, e.g. alt="Description of image", or alt="" if decorative.

#### 🔴 Before (Violating Code):
```html
<img class="product-img" src="data:image/svg+xml;utf8,&lt;svg xmlns='http://www.w3.org/2000/svg' width='80' height='80' fill='%236366f1'&gt;&lt;rect width='100%' height='100%'/&gt;&lt;/svg&gt;"/> ... </img>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<img class="product-img" src="data:image/svg+xml;utf8,&lt;svg xmlns='http://www.w3.org/2000/svg' width='80' height='80' fill='%236366f1'&gt;&lt;rect width='100%' height='100%'/&gt;&lt;/svg&gt;" alt="Ultra-Light Wireless Noise Cancelling Headphones"> ... </img>
```

---

### 2. Missing Image Alternative Text (`WCAG-1.1.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `main.checkout-container > section:nth-of-type(1) > div.product-row:nth-of-type(2) > img.product-img`
- **Issue:** The <img> element is completely missing an 'alt' attribute. Screen readers cannot describe the visual content to users with visual impairments and may announce the raw image URL.
- **Remediation Strategy:** Add a descriptive alt attribute, e.g. alt="Description of image", or alt="" if decorative.

#### 🔴 Before (Violating Code):
```html
<img class="product-img" src="data:image/svg+xml;utf8,&lt;svg xmlns='http://www.w3.org/2000/svg' width='80' height='80' fill='%2310b981'&gt;&lt;rect width='100%' height='100%'/&gt;&lt;/svg&gt;"/> ... </img>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<img class="product-img" src="data:image/svg+xml;utf8,&lt;svg xmlns='http://www.w3.org/2000/svg' width='80' height='80' fill='%2310b981'&gt;&lt;rect width='100%' height='100%'/&gt;&lt;/svg&gt;" alt="Braided Fast-Charging USB-C Cable (2m)"> ... </img>
```

---

### 3. Missing Form Input Label (`WCAG-1.3.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#cardholder-name`
- **Issue:** Form control <input> lacks an accessible programmatic label (<label for='...'>, wrapping label, or aria-label). Relying solely on placeholder='Cardholder Full Name' violates WCAG 3.3.2 because placeholders disappear on user input and are not reliably announced by all screen readers.
- **Remediation Strategy:** <label for="cardholder-name">Field Label</label> or aria-label="Field Label"

#### 🔴 Before (Violating Code):
```html
<input class="form-control" id="cardholder-name" placeholder="Cardholder Full Name" type="text"/>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<label for="cardholder-name" class="form-label">Cardholder Full Name</label>
<input class="form-control" id="cardholder-name" placeholder="Cardholder Full Name" type="text"/>
```

---

### 4. Missing Form Input Label (`WCAG-1.3.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#cc-number`
- **Issue:** Form control <input> lacks an accessible programmatic label (<label for='...'>, wrapping label, or aria-label). Relying solely on placeholder='Credit Card Number (16 digits)' violates WCAG 3.3.2 because placeholders disappear on user input and are not reliably announced by all screen readers.
- **Remediation Strategy:** <label for="cc-number">Field Label</label> or aria-label="Field Label"

#### 🔴 Before (Violating Code):
```html
<input class="form-control" id="cc-number" placeholder="Credit Card Number (16 digits)" type="text"/>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<label for="cc-number" class="form-label">Credit Card Number (16 digits)</label>
<input class="form-control" id="cc-number" placeholder="Credit Card Number (16 digits)" type="text"/>
```

---

### 5. Missing Form Input Label (`WCAG-1.3.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#cc-expiry`
- **Issue:** Form control <input> lacks an accessible programmatic label (<label for='...'>, wrapping label, or aria-label). Relying solely on placeholder='MM/YY' violates WCAG 3.3.2 because placeholders disappear on user input and are not reliably announced by all screen readers.
- **Remediation Strategy:** <label for="cc-expiry">Field Label</label> or aria-label="Field Label"

#### 🔴 Before (Violating Code):
```html
<input class="form-control" id="cc-expiry" placeholder="MM/YY" type="text"/>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<label for="cc-expiry" class="form-label">MM/YY</label>
<input class="form-control" id="cc-expiry" placeholder="MM/YY" type="text"/>
```

---

### 6. Missing Form Input Label (`WCAG-1.3.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#cc-cvv`
- **Issue:** Form control <input> lacks an accessible programmatic label (<label for='...'>, wrapping label, or aria-label). Relying solely on placeholder='CVV' violates WCAG 3.3.2 because placeholders disappear on user input and are not reliably announced by all screen readers.
- **Remediation Strategy:** <label for="cc-cvv">Field Label</label> or aria-label="Field Label"

#### 🔴 Before (Violating Code):
```html
<input class="form-control" id="cc-cvv" placeholder="CVV" type="password"/>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<label for="cc-cvv" class="form-label">CVV</label>
<input class="form-control" id="cc-cvv" placeholder="CVV" type="password"/>
```

---

### 7. Insufficient Color Contrast Ratio (`WCAG-1.4.3`)
- **Severity:** `Serious`
- **Target DOM Selector:** `#btn-submit-payment`
- **Issue:** Computed contrast ratio is 2.18:1, failing WCAG AA threshold of 4.5:1 (computed foreground 'rgb(156, 163, 175)' on background 'rgb(254, 240, 138)'). Users with low vision or color blindness cannot comfortably perceive this text.
- **Remediation Strategy:** Adjust text or background color to satisfy minimum 4.5:1 contrast ratio.

#### 🔴 Before (Violating Code):
```html
<button type="submit" id="btn-submit-payment" class="btn-pay-broken">
            Pay Now $228.00
          </button>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<button type="submit" id="btn-submit-payment" class="btn-pay-broken" style="background-color: #15803d; color: #ffffff; font-weight: 700;">
  Pay Now $228.00
</button>
```

---

## Document: `02_saas_dashboard.html`
**Total Violations Remediated:** 5 | **Status:** FAILED

### 1. Insufficient Color Contrast Ratio (`WCAG-1.4.3`)
- **Severity:** `Serious`
- **Target DOM Selector:** `main.dashboard-content > div.card-grid > div.card:nth-of-type(1) > span`
- **Issue:** Computed contrast ratio is 3.3:1, failing WCAG AA threshold of 4.5:1 (computed foreground 'rgb(22, 163, 74)' on background 'rgb(255, 255, 255)'). Users with low vision or color blindness cannot comfortably perceive this text.
- **Remediation Strategy:** Adjust text or background color to satisfy minimum 4.5:1 contrast ratio.

#### 🔴 Before (Violating Code):
```html
<span style="color: #16a34a;">↑ Optimal performance</span>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<span style="color: #15803d; font-weight: 600;">↑ Optimal performance</span>
```

---

### 2. Insufficient Color Contrast Ratio (`WCAG-1.4.3`)
- **Severity:** `Serious`
- **Target DOM Selector:** `#cluster-status-badge`
- **Issue:** Computed contrast ratio is 2.45:1, failing WCAG AA threshold of 4.5:1 (computed foreground 'rgb(148, 163, 184)' on background 'rgb(248, 250, 252)'). Users with low vision or color blindness cannot comfortably perceive this text.
- **Remediation Strategy:** Adjust text or background color to satisfy minimum 4.5:1 contrast ratio.

#### 🔴 Before (Violating Code):
```html
<span class="status-badge-inactive" id="cluster-status-badge">Standby Mode</span>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<span class="status-badge-inactive" id="cluster-status-badge" style="background-color: #e2e8f0; color: #1e293b; font-weight: 600;">Standby Mode</span>
```

---

### 3. Heading Hierarchy Skip (`WCAG-1.3.1H`)
- **Severity:** `Moderate`
- **Target DOM Selector:** `main.dashboard-content > h4`
- **Issue:** Heading structure jumps from <h1> directly to <h4>, skipping <h2>. Skipping heading levels creates a disjointed outline in screen reader navigation palettes.
- **Remediation Strategy:** Change <h4> to <h2> or restructure document sections.

#### 🔴 Before (Violating Code):
```html
<h4>Real-time Infrastructure Status</h4>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<h2>Real-time Infrastructure Status</h2>
```

---

### 4. Button Missing Accessible Name (`WCAG-4.1.2`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#notifications-btn`
- **Issue:** The <button> contains no readable text, aria-label, title, or accessible image/svg alt/title. Screen readers will announce an unlabelled button, preventing users from understanding its action.
- **Remediation Strategy:** Add aria-label="Action Name" or include descriptive text.

#### 🔴 Before (Violating Code):
```html
<button class="icon-btn" id="notifications-btn"> ... </button>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<button class="icon-btn" id="notifications-btn" aria-label="View user notifications"> ... </button>
```

---

### 5. Button Missing Accessible Name (`WCAG-4.1.2`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#settings-btn`
- **Issue:** The <button> contains no readable text, aria-label, title, or accessible image/svg alt/title. Screen readers will announce an unlabelled button, preventing users from understanding its action.
- **Remediation Strategy:** Add aria-label="Action Name" or include descriptive text.

#### 🔴 Before (Violating Code):
```html
<button class="icon-btn" id="settings-btn" style="margin-left: 0.5rem;"> ... </button>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<button class="icon-btn" id="settings-btn" style="margin-left: 0.5rem;" aria-label="Open system settings"> ... </button>
```

---

## Document: `03_signup_form.html`
**Total Violations Remediated:** 6 | **Status:** FAILED

### 1. Missing Form Input Label (`WCAG-1.3.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#fullname-input`
- **Issue:** Form control <input> lacks an accessible programmatic label (<label for='...'>, wrapping label, or aria-label). Relying solely on placeholder='Full legal name' violates WCAG 3.3.2 because placeholders disappear on user input and are not reliably announced by all screen readers.
- **Remediation Strategy:** <label for="fullname-input">Field Label</label> or aria-label="Field Label"

#### 🔴 Before (Violating Code):
```html
<input id="fullname-input" name="fullname" placeholder="Full legal name" type="text"/>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<label for="fullname-input" class="form-label">Full legal name</label>
<input id="fullname-input" name="fullname" placeholder="Full legal name" type="text"/>
```

---

### 2. Missing Form Input Label (`WCAG-1.3.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#email-input`
- **Issue:** Form control <input> lacks an accessible programmatic label (<label for='...'>, wrapping label, or aria-label). Relying solely on placeholder='work.email@company.com' violates WCAG 3.3.2 because placeholders disappear on user input and are not reliably announced by all screen readers.
- **Remediation Strategy:** <label for="email-input">Field Label</label> or aria-label="Field Label"

#### 🔴 Before (Violating Code):
```html
<input id="email-input" name="email" placeholder="work.email@company.com" type="email"/>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<label for="email-input" class="form-label">work.email@company.com</label>
<input id="email-input" name="email" placeholder="work.email@company.com" type="email"/>
```

---

### 3. Missing Form Input Label (`WCAG-1.3.1`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#password-input`
- **Issue:** Form control <input> lacks an accessible programmatic label (<label for='...'>, wrapping label, or aria-label). Relying solely on placeholder='Create secure password' violates WCAG 3.3.2 because placeholders disappear on user input and are not reliably announced by all screen readers.
- **Remediation Strategy:** <label for="password-input">Field Label</label> or aria-label="Field Label"

#### 🔴 Before (Violating Code):
```html
<input id="password-input" name="password" placeholder="Create secure password" tabindex="5" type="password"/>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<label for="password-input" class="form-label">Create secure password</label>
<input id="password-input" name="password" placeholder="Create secure password" tabindex="5" type="password"/>
```

---

### 4. Non-Focusable Interactive Element (`WCAG-4.1.2`)
- **Severity:** `Critical`
- **Target DOM Selector:** `#fake-submit-btn`
- **Issue:** Element <div role='button'> specifies an interactive role but lacks tabindex='0'. Keyboard-only users cannot tab to or activate this custom element.
- **Remediation Strategy:** Replace with native <button> or add tabindex="0" and keyboard activation handlers (Enter/Space).

#### 🔴 Before (Violating Code):
```html
<div class="btn-fake-button" id="fake-submit-btn" role="button">
          Sign Up with Workspace
        </div>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<button type="submit" id="fake-submit-btn" class="btn-fake-button">Sign Up with Workspace</button>
```

---

### 5. Disruptive Positive Tabindex (`WCAG-AI-2.1.2`)
- **Severity:** `Serious`
- **Target DOM Selector:** `#password-input`
- **Issue:** Element specifies positive tabindex='5'. Positive tabindex forces an unnatural focus sequence, bypassing preceding interactive elements for keyboard navigators.
- **Remediation Strategy:** Use tabindex="0" to preserve natural DOM order or restructure HTML hierarchy.

#### 🔴 Before (Violating Code):
```html
<input id="password-input" name="password" placeholder="Create secure password" tabindex="5" type="password"/>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<input id="password-input" name="password" placeholder="Create secure password" tabindex="0" type="password"/>
```

---

### 6. Interactive Element Unreachable via Keyboard (`WCAG-AI-2.1.2`)
- **Severity:** `Serious`
- **Target DOM Selector:** `#fake-submit-btn`
- **Issue:** Interactive control '#fake-submit-btn' was not reachable during simulated keyboard Tab traversal. Keyboard-dependent users cannot access or activate this function.
- **Remediation Strategy:** Ensure element is in DOM tab sequence (tabindex="0") and not suppressed by CSS pointer-events.

#### 🔴 Before (Violating Code):
```html
<div class="btn-fake-button" id="fake-submit-btn" role="button">
          Sign Up with Workspace
        </div>
```

#### 🟢 After (Accessible Drop-in Patch):
```html
<div class="btn-fake-button" id="fake-submit-btn" role="button">
          Sign Up with Workspace
        </div>
```

---
