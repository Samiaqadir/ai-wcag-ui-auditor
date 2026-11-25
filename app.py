"""
Interactive Streamlit QA Auditor Dashboard for AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor.
Day-3 Suite:
- Side-by-side HTML diff viewers with built-in copy controls
- Human QA review & triage workflows (Pending, Confirmed Defect, False Positive, Won't Fix)
- Dynamic WCAG 2.1 AA Compliance Score recalculation (excluding False Positives)
- Visual Layout & DOM Regression Baseline comparisons
- One-click multi-format report exports (HTML, Markdown, CSV)
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import urllib.request
import streamlit as st

# Ensure base project path is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from auditor.models import Violation, Severity, PageAuditResult, RegressionDiffReport
from auditor.rules import audit_page_file
from auditor.regression import compare_page_snapshots
from auditor.exporter import (
    export_to_html,
    export_to_markdown,
    export_to_csv,
    calculate_wcag_score,
    get_violation_key,
    get_compliance_grade,
)

# =========================================================================
# Page Configuration & Modern Theme Styling
# =========================================================================
st.set_page_config(
    page_title="AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End Styling
st.markdown("""
<style>
    /* Metric & KPI Cards */
    .metric-card-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-card-title {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    .metric-card-value {
        font-size: 28px;
        font-weight: 800;
        color: #ffffff;
        line-height: 1.1;
    }
    .metric-card-sub {
        font-size: 11px;
        color: #64748b;
        margin-top: 4px;
    }
    /* Severity Badges */
    .badge-critical {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #ef4444;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }
    .badge-serious {
        background-color: #ffedd5;
        color: #9a3412;
        border: 1px solid #f97316;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }
    .badge-moderate {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #f59e0b;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }
    .badge-minor {
        background-color: #e0f2fe;
        color: #075985;
        border: 1px solid #0ea5e9;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }
    /* Triage Status Badges */
    .badge-confirmed {
        background-color: rgba(220, 38, 38, 0.15);
        color: #f87171;
        border: 1px solid #ef4444;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-false-positive {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid #10b981;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-wont-fix {
        background-color: rgba(107, 114, 128, 0.15);
        color: #9ca3af;
        border: 1px solid #6b7280;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-pending {
        background-color: rgba(202, 138, 4, 0.15);
        color: #facc15;
        border: 1px solid #eab308;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
    }
    /* Card Container */
    .issue-wrapper {
        border: 1px solid #334155;
        border-radius: 12px;
        background: #1e293b;
        padding: 16px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# Session State Initialization
# =========================================================================
if "audit_result" not in st.session_state:
    st.session_state.audit_result = None
if "triage_data" not in st.session_state:
    st.session_state.triage_data = {}
if "regression_report" not in st.session_state:
    st.session_state.regression_report = None
if "current_page_name" not in st.session_state:
    st.session_state.current_page_name = "01_ecommerce_checkout.html"

TEST_PAGES_DIR = BASE_DIR / "test_pages"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================================
# Sidebar Controls & Input Selector
# =========================================================================
st.sidebar.image("https://img.icons8.com/fluency/96/accessibility.png", width=64)
st.sidebar.title("QA Audit Studio")
st.sidebar.caption("WCAG 2.1 Level AA & UI Regression")
st.sidebar.markdown("---")

input_mode = st.sidebar.radio(
    "1. Select Audit Input Mode:",
    [
        "Sample Test Pages (/test_pages/)",
        "Upload Local HTML File",
        "Live URL / Raw HTML Paste",
    ],
    index=0,
)

target_file_path: Optional[Path] = None
page_display_name = ""

if input_mode == "Sample Test Pages (/test_pages/)":
    sample_files = sorted([f.name for f in TEST_PAGES_DIR.glob("*.html")])
    if not sample_files:
        st.sidebar.error("No sample HTML files found in /test_pages/")
    else:
        selected_sample = st.sidebar.selectbox("Choose Target HTML Document:", sample_files, index=0)
        target_file_path = TEST_PAGES_DIR / selected_sample
        page_display_name = selected_sample

elif input_mode == "Upload Local HTML File":
    uploaded_file = st.sidebar.file_uploader("Upload an HTML page to audit:", type=["html", "htm"])
    if uploaded_file is not None:
        temp_path = OUTPUT_DIR / f"uploaded_{uploaded_file.name}"
        temp_path.write_bytes(uploaded_file.getbuffer())
        target_file_path = temp_path
        page_display_name = uploaded_file.name
    else:
        st.sidebar.info("Upload an .html or .htm file to begin audit.")

elif input_mode == "Live URL / Raw HTML Paste":
    paste_mode = st.sidebar.radio("Input Type:", ["Raw HTML Markup", "Live HTTP URL"])
    if paste_mode == "Raw HTML Markup":
        raw_html = st.sidebar.text_area("Paste HTML source snippet:", height=150, placeholder="<html><body>...</body></html>")
        if raw_html.strip():
            temp_path = OUTPUT_DIR / "pasted_input.html"
            temp_path.write_text(raw_html, encoding="utf-8")
            target_file_path = temp_path
            page_display_name = "pasted_snippet.html"
    else:
        url_input = st.sidebar.text_input("Enter live URL to fetch & audit:", placeholder="https://example.com")
        if url_input.strip():
            if st.sidebar.button("Fetch Live Page"):
                try:
                    req = urllib.request.Request(url_input, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    with urllib.request.urlopen(req) as response:
                        fetched_html = response.read().decode("utf-8", errors="ignore")
                    temp_path = OUTPUT_DIR / "fetched_url.html"
                    temp_path.write_text(fetched_html, encoding="utf-8")
                    target_file_path = temp_path
                    page_display_name = url_input
                    st.sidebar.success("Fetched successfully!")
                except Exception as e:
                    st.sidebar.error(f"Failed to fetch URL: {e}")

st.sidebar.markdown("---")

# Optional UI Regression Baseline Comparison
st.sidebar.subheader("2. UI Regression Baseline")
enable_regression = st.sidebar.checkbox(
    "Enable Baseline Comparison",
    value=True if page_display_name == "01_ecommerce_checkout_modified.html" else False,
    help="Renders both pages via Playwright to detect geometry layout shifts, CSS mutations, and DOM diffs."
)

baseline_file_path: Optional[Path] = None
if enable_regression:
    all_baseline_candidates = sorted([f.name for f in TEST_PAGES_DIR.glob("*.html") if "_modified" not in f.name])
    selected_baseline = st.sidebar.selectbox("Choose Baseline Page:", all_baseline_candidates, index=0)
    baseline_file_path = TEST_PAGES_DIR / selected_baseline
    st.sidebar.caption(f"Comparing target against baseline `{selected_baseline}`")

st.sidebar.markdown("---")

# Run Audit Button
run_audit_clicked = st.sidebar.button("🚀 Run WCAG & UI Audit", type="primary", use_container_width=True)

if run_audit_clicked:
    if target_file_path and target_file_path.exists():
        with st.spinner(f"Running full 10-rule WCAG 2.1 AA audit on `{page_display_name}`..."):
            audit_res = audit_page_file(target_file_path)
            st.session_state.audit_result = audit_res
            st.session_state.current_page_name = page_display_name

            # Initialize triage state for new findings if not already present
            for idx, v in enumerate(audit_res.violations):
                key = get_violation_key(v, idx)
                if key not in st.session_state.triage_data:
                    st.session_state.triage_data[key] = {
                        "status": "Pending",
                        "notes": "",
                    }

            # Optional Regression Diff
            if enable_regression and baseline_file_path and baseline_file_path.exists():
                with st.spinner("Analyzing Playwright visual layout shifts & DOM regressions..."):
                    reg_rep = compare_page_snapshots(baseline_file_path, target_file_path)
                    st.session_state.regression_report = reg_rep
            else:
                st.session_state.regression_report = None

            st.sidebar.success(f"Audit completed: {audit_res.total_violations} findings detected.")
    else:
        st.sidebar.error("Please provide or select a valid HTML file to audit.")


# Auto-run sample on first load if no result exists yet
if st.session_state.audit_result is None:
    default_sample = TEST_PAGES_DIR / "01_ecommerce_checkout.html"
    if default_sample.exists():
        audit_res = audit_page_file(default_sample)
        st.session_state.audit_result = audit_res
        st.session_state.current_page_name = "01_ecommerce_checkout.html"
        for idx, v in enumerate(audit_res.violations):
            key = get_violation_key(v, idx)
            st.session_state.triage_data[key] = {
                "status": "Pending",
                "notes": "",
            }


# =========================================================================
# Main Dashboard Interface
# =========================================================================
result: PageAuditResult = st.session_state.audit_result
triage_data: Dict[str, Dict[str, Any]] = st.session_state.triage_data

# Header
st.title("🛡️ AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor")
st.caption(f"Target Document: **`{st.session_state.current_page_name}`** | Engine: **Day-3 Interactive QA Triage Edition**")

# Calculate Dynamic WCAG Compliance Score (Automatically excluding False Positives!)
score = calculate_wcag_score(result.violations, triage_data)
grade = get_compliance_grade(score)

# Calculate Metric Counts
total_count = len(result.violations)
confirmed_count = sum(1 for idx, v in enumerate(result.violations) if triage_data.get(get_violation_key(v, idx), {}).get("status") == "Confirmed Defect")
false_pos_count = sum(1 for idx, v in enumerate(result.violations) if triage_data.get(get_violation_key(v, idx), {}).get("status") == "False Positive")
wont_fix_count = sum(1 for idx, v in enumerate(result.violations) if triage_data.get(get_violation_key(v, idx), {}).get("status") == "Won't Fix")
pending_count = sum(1 for idx, v in enumerate(result.violations) if triage_data.get(get_violation_key(v, idx), {}).get("status") == "Pending")

crit_ser_count = 0
for idx, v in enumerate(result.violations):
    key = get_violation_key(v, idx)
    st_val = triage_data.get(key, {}).get("status", "Pending")
    sev = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
    if sev in [Severity.CRITICAL.value, Severity.SERIOUS.value] and st_val != "False Positive":
        crit_ser_count += 1

# =========================================================================
# Top KPI Header & WCAG Compliance Score Badge
# =========================================================================
col_score, col_total, col_defects, col_crit, col_fp = st.columns([1.3, 1, 1, 1, 1])

with col_score:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 2px solid {grade['color']}; border-radius: 12px; padding: 14px 20px; text-align: center;">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px;">WCAG Compliance Score</div>
        <div style="font-size: 36px; font-weight: 900; color: {grade['color']}; line-height: 1;">{score}%</div>
        <div style="margin-top: 4px; display: inline-block; background: {grade['color']}; color: #ffffff; padding: 2px 10px; border-radius: 9999px; font-size: 10px; font-weight: 700;">
            {grade['grade']} ({grade['label']})
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_total:
    st.markdown(f"""
    <div class="metric-card-container">
        <div class="metric-card-title">Total Findings</div>
        <div class="metric-card-value">{total_count}</div>
        <div class="metric-card-sub">10-Rule Suite Scanned</div>
    </div>
    """, unsafe_allow_html=True)

with col_defects:
    st.markdown(f"""
    <div class="metric-card-container">
        <div class="metric-card-title">Confirmed Defects</div>
        <div class="metric-card-value" style="color: #f87171;">{confirmed_count}</div>
        <div class="metric-card-sub">Engineering Action Items</div>
    </div>
    """, unsafe_allow_html=True)

with col_crit:
    st.markdown(f"""
    <div class="metric-card-container">
        <div class="metric-card-title">Critical & Serious</div>
        <div class="metric-card-value" style="color: #fb923c;">{crit_ser_count}</div>
        <div class="metric-card-sub">Assistive Tech Blockers</div>
    </div>
    """, unsafe_allow_html=True)

with col_fp:
    st.markdown(f"""
    <div class="metric-card-container">
        <div class="metric-card-title">False Positives</div>
        <div class="metric-card-value" style="color: #34d399;">{false_pos_count}</div>
        <div class="metric-card-sub">Filtered from Score</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# =========================================================================
# One-Click Report Export Bar (Top)
# =========================================================================
export_col1, export_col2, export_col3 = st.columns(3)

# Generate export payloads live reflecting current triage selections
html_report_data = export_to_html(
    result,
    st.session_state.triage_data,
    page_name=st.session_state.current_page_name,
    regression_report=st.session_state.regression_report,
)
md_report_data = export_to_markdown(
    result,
    st.session_state.triage_data,
    page_name=st.session_state.current_page_name,
)
csv_report_data = export_to_csv(
    result,
    st.session_state.triage_data,
)

safe_doc_slug = st.session_state.current_page_name.replace(".html", "").replace(" ", "_")

with export_col1:
    st.download_button(
        label="📥 Download HTML Report (.html)",
        data=html_report_data,
        file_name=f"qa_audit_{safe_doc_slug}.html",
        mime="text/html",
        use_container_width=True,
    )

with export_col2:
    st.download_button(
        label="📝 Download Markdown Report (.md)",
        data=md_report_data,
        file_name=f"qa_audit_{safe_doc_slug}.md",
        mime="text/markdown",
        use_container_width=True,
    )

with export_col3:
    st.download_button(
        label="📊 Download CSV Report (.csv)",
        data=csv_report_data,
        file_name=f"qa_audit_{safe_doc_slug}.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.markdown("---")

# =========================================================================
# Optional Visual Layout & DOM Regression Diff Section
# =========================================================================
if st.session_state.regression_report is not None:
    reg: RegressionDiffReport = st.session_state.regression_report
    with st.expander(f"📐 Visual Layout & DOM Regression Diff (Baseline: `{reg.baseline_page}` vs Modified: `{reg.modified_page}`)", expanded=True):
        r_col1, r_col2, r_col3, r_col4 = st.columns(4)
        r_col1.metric("Layout Shifts", reg.total_layout_shifts)
        r_col2.metric("Style Mutations", reg.total_style_regressions)
        r_col3.metric("Added Elements", len(reg.structural_changes.added_elements))
        r_col4.metric("Removed Elements", len(reg.structural_changes.removed_elements))

        if reg.layout_shifts:
            st.markdown("##### 📍 Detected Layout Shifts (Geometry Deltas):")
            shift_rows = []
            for s in reg.layout_shifts:
                shift_rows.append({
                    "Target DOM Selector": s.dom_selector,
                    "Shift Description": s.shift_description,
                    "ΔX (px)": s.delta_x,
                    "ΔY (px)": s.delta_y,
                    "ΔWidth (px)": s.delta_width,
                    "ΔHeight (px)": s.delta_height,
                })
            st.dataframe(shift_rows, use_container_width=True)

        if reg.style_regressions:
            st.markdown("##### 🎨 Computed Style Mutations:")
            style_rows = []
            for st_item in reg.style_regressions:
                style_rows.append({
                    "Target Selector": st_item.dom_selector,
                    "Property": st_item.property_name,
                    "Baseline Value": st_item.baseline_value,
                    "Modified Value": st_item.modified_value,
                    "Impact": st_item.impact,
                })
            st.dataframe(style_rows, use_container_width=True)

    st.markdown("---")


# =========================================================================
# Severity & Triage Filter Bar
# =========================================================================
f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 2])

with f_col1:
    severity_filter = st.selectbox(
        "🔍 Filter by Severity:",
        ["All", "Critical", "Serious", "Moderate", "Minor"],
        index=0,
    )

with f_col2:
    triage_filter = st.selectbox(
        "📋 Filter by QA Triage Status:",
        ["All", "Pending", "Confirmed Defect", "False Positive", "Won't Fix"],
        index=0,
    )

with f_col3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("⚡ Mark All Pending as Confirmed Defects", help="Quick bulk triage action for active defects"):
        for idx, v in enumerate(result.violations):
            key = get_violation_key(v, idx)
            if st.session_state.triage_data[key]["status"] == "Pending":
                st.session_state.triage_data[key]["status"] = "Confirmed Defect"
                if not st.session_state.triage_data[key]["notes"]:
                    st.session_state.triage_data[key]["notes"] = "Confirmed Defect: Verified blocker for remediation."
        st.rerun()


# =========================================================================
# Interactive Issue Cards with Code Diff & Human QA Triage
# =========================================================================
st.markdown("### 📋 Detailed WCAG Violations & Context-Aware Code Patches")

# Apply Filters
filtered_violations = []
for idx, v in enumerate(result.violations):
    key = get_violation_key(v, idx)
    curr_triage = st.session_state.triage_data.get(key, {})
    curr_status = curr_triage.get("status", "Pending")

    sev_str = v.severity.value if hasattr(v.severity, "value") else str(v.severity)

    if severity_filter != "All" and sev_str != severity_filter:
        continue
    if triage_filter != "All" and curr_status != triage_filter:
        continue

    filtered_violations.append((idx, v, key))

if not filtered_violations:
    st.info(f"No violations match the selected filters (Severity: `{severity_filter}`, Triage: `{triage_filter}`).")
else:
    st.caption(f"Showing **{len(filtered_violations)}** of **{len(result.violations)}** findings:")

    for idx, v, key in filtered_violations:
        curr_triage = st.session_state.triage_data.get(key, {"status": "Pending", "notes": ""})
        curr_status = curr_triage.get("status", "Pending")
        curr_notes = curr_triage.get("notes", "")

        sev_str = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
        sev_badge_class = f"badge-{sev_str.lower()}"

        triage_badge_class = {
            "Confirmed Defect": "badge-confirmed",
            "False Positive": "badge-false-positive",
            "Won't Fix": "badge-wont-fix",
            "Pending": "badge-pending",
        }.get(curr_status, "badge-pending")

        # Container card
        with st.container():
            st.markdown(f"""
            <div style="border: 1px solid #334155; border-radius: 12px; background: #1e293b; padding: 16px 20px; margin-top: 14px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <span style="font-family: monospace; font-size: 13px; font-weight: 700; color: #60a5fa; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); padding: 2px 8px; border-radius: 6px; margin-right: 8px;">{v.rule_id}</span>
                        <strong style="font-size: 16px; color: #f8fafc;">{v.rule_name}</strong>
                    </div>
                    <div>
                        <span class="{sev_badge_class}">{sev_str}</span>
                        &nbsp;
                        <span class="{triage_badge_class}">● {curr_status}</span>
                    </div>
                </div>
                <div style="margin-top: 10px; font-size: 13px; color: #cbd5e1;">
                    <span style="color: #94a3b8; font-weight: 600;">Target Selector:</span>
                    <code style="background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #38bdf8;">{v.dom_selector}</code>
                </div>
                <div style="margin-top: 6px; font-size: 13px; color: #e2e8f0;">
                    <strong>Issue:</strong> {v.issue_explanation}
                </div>
                <div style="margin-top: 4px; font-size: 13px; color: #94a3b8;">
                    <strong>Remediation Strategy:</strong> {v.suggested_fix}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Side-by-Side 2-Column Code Diff View
            diff_col1, diff_col2 = st.columns(2)

            with diff_col1:
                st.markdown("**🔴 Original Non-Compliant HTML:**")
                before_code = v.before_html or v.raw_html_snippet or "<!-- No raw snippet available -->"
                st.code(before_code, language="html")

            with diff_col2:
                st.markdown("**🟢 Recommended Accessible Patch:** *(Hover to copy)*")
                after_code = v.after_html or v.suggested_fix or "<!-- Patch pending -->"
                st.code(after_code, language="html")

            # Human QA Review & Triage Controls
            with st.expander("🛠️ Human QA Triage & Reviewer Notes", expanded=(curr_status == "Pending")):
                t_col1, t_col2 = st.columns([1, 2])

                with t_col1:
                    status_options = ["Pending", "Confirmed Defect", "False Positive", "Won't Fix"]
                    curr_idx = status_options.index(curr_status) if curr_status in status_options else 0
                    new_status = st.selectbox(
                        "QA Triage Decision:",
                        status_options,
                        index=curr_idx,
                        key=f"status_select_{key}",
                        help="False Positives are automatically excluded from compliance score penalty."
                    )

                with t_col2:
                    new_notes = st.text_input(
                        "QA Reviewer Commentary / Ticket Ref:",
                        value=curr_notes,
                        placeholder="e.g. Confirmed screen-reader barrier; ticket JIRA-402 filed",
                        key=f"notes_input_{key}",
                    )

                # Persist changes to session state if changed
                if new_status != curr_status or new_notes != curr_notes:
                    st.session_state.triage_data[key] = {
                        "status": new_status,
                        "notes": new_notes,
                    }
                    st.rerun()

            st.markdown("<hr style='border: none; border-top: 1px solid #334155; margin: 16px 0;'/>", unsafe_allow_html=True)


# =========================================================================
# One-Click Report Export Bar (Bottom)
# =========================================================================
st.markdown("### 💾 Export Triaged Executive QA Reports")
b_col1, b_col2, b_col3 = st.columns(3)

with b_col1:
    st.download_button(
        label="📥 Download HTML Report (.html)",
        data=html_report_data,
        file_name=f"qa_audit_{safe_doc_slug}.html",
        mime="text/html",
        key="btn_dl_html_bottom",
        use_container_width=True,
    )

with b_col2:
    st.download_button(
        label="📝 Download Markdown Report (.md)",
        data=md_report_data,
        file_name=f"qa_audit_{safe_doc_slug}.md",
        mime="text/markdown",
        key="btn_dl_md_bottom",
        use_container_width=True,
    )

with b_col3:
    st.download_button(
        label="📊 Download CSV Report (.csv)",
        data=csv_report_data,
        file_name=f"qa_audit_{safe_doc_slug}.csv",
        mime="text/csv",
        key="btn_dl_csv_bottom",
        use_container_width=True,
    )

st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
st.caption("AI Accessibility (WCAG 2.1 AA) & UI Regression Auditor • Day-3 QA Studio • Built with Streamlit")
