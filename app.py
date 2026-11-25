"""
Interactive Streamlit QA Auditor Dashboard.
Features:
- Multi-mode input (Sample Test Pages, Upload File, Paste HTML/URL)
- Dynamic WCAG 2.1 AA Compliance Score (reactively updating on triage)
- Human QA review controls (Confirmed Defect, False Positive, Won't Fix)
- Side-by-side Before/After HTML code diff viewers with built-in copy
- Visual layout and DOM regression diff viewer
- One-click multi-format report exports (HTML, Markdown, CSV)
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from auditor.models import (
    PageAuditResult,
    Violation,
    Severity,
    TriageStatus,
    RegressionDiffReport,
)
from auditor.rules import audit_page_file
from auditor.regression import compare_page_snapshots
from auditor.exporter import export_to_html, export_to_markdown, export_to_csv


# =========================================================================
# Streamlit Page Configuration & Modern Styling
# =========================================================================
st.set_page_config(
    page_title="AI Accessibility & UI Regression Auditor",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  /* Header styling */
  .main-header {
    font-size: 2.1rem;
    font-weight: 800;
    color: #1e1b4b;
    margin-bottom: 0.2rem;
    letter-spacing: -0.02em;
  }
  .sub-header {
    font-size: 0.95rem;
    color: #475569;
    margin-bottom: 1.5rem;
  }
  /* Compliance score card */
  .score-box {
    background: linear-gradient(135deg, #f8fafc, #edf2f7);
    border: 2px solid #cbd5e1;
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
  }
  .score-number {
    font-size: 2.8rem;
    font-weight: 900;
    line-height: 1;
  }
  .score-caption {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #64748b;
    margin-top: 0.35rem;
  }
  /* Badges */
  .badge-crit { background-color: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem; }
  .badge-ser { background-color: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem; }
  .badge-mod { background-color: #e0f2fe; color: #075985; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem; }
  
  .badge-triage-conf { background-color: #fecaca; color: #b91c1c; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem; }
  .badge-triage-fp { background-color: #bbf7d0; color: #15803d; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem; }
  .badge-triage-wf { background-color: #e2e8f0; color: #334155; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem; }
  .badge-triage-pend { background-color: #fef08a; color: #854d0e; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.75rem; }

  .selector-chip {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.8rem;
    background: #f1f5f9;
    padding: 3px 8px;
    border-radius: 4px;
    color: #334155;
    word-break: break-all;
  }
</style>
""", unsafe_allow_html=True)


# =========================================================================
# Sidebar Controls & Input Modes
# =========================================================================
st.sidebar.markdown("### 🛠️ Audit Configuration")
st.sidebar.markdown("Configure target document and inspection criteria.")

test_pages_dir = BASE_DIR / "test_pages"
sample_files = sorted([f.name for f in test_pages_dir.glob("*.html") if not f.name.startswith("temp_")])

input_mode = st.sidebar.radio(
    "Select Input Source Mode:",
    ["Sample Test Pack", "Upload HTML File", "Raw HTML Paste / URL"],
    index=0,
)

target_file_path = None
target_file_name = None

if input_mode == "Sample Test Pack":
    selected_sample = st.sidebar.selectbox("Choose Sample Test Page:", sample_files, index=0)
    target_file_path = test_pages_dir / selected_sample
    target_file_name = selected_sample

elif input_mode == "Upload HTML File":
    uploaded = st.sidebar.file_uploader("Upload HTML Document:", type=["html", "htm"])
    if uploaded:
        temp_dest = test_pages_dir / f"temp_{uploaded.name}"
        temp_dest.write_bytes(uploaded.getvalue())
        target_file_path = temp_dest
        target_file_name = uploaded.name

elif input_mode == "Raw HTML Paste / URL":
    sub_mode = st.sidebar.radio("Input Type:", ["Paste Raw HTML", "Fetch Live URL"], index=0)
    if sub_mode == "Paste Raw HTML":
        pasted_content = st.sidebar.text_area("Paste HTML source:", height=150, placeholder="<!DOCTYPE html><html>...")
        if pasted_content.strip():
            temp_dest = test_pages_dir / "temp_pasted_audit.html"
            temp_dest.write_text(pasted_content, encoding="utf-8")
            target_file_path = temp_dest
            target_file_name = "pasted_document.html"
    else:
        url_input = st.sidebar.text_input("Enter URL:", placeholder="http://127.0.0.1:8000/...")
        if url_input.strip():
            st.sidebar.info("URL mode will be rendered in Playwright.")
            target_file_path = url_input
            target_file_name = url_input.split("/")[-1] or "live_page.html"

# Optional UI Regression Diffing
st.sidebar.markdown("---")
enable_regression = st.sidebar.checkbox("Enable UI Regression Diffing", value=False)
baseline_file_path = None

if enable_regression:
    baseline_options = [f for f in sample_files if "_modified" not in f]
    selected_baseline = st.sidebar.selectbox("Baseline Snapshot:", baseline_options, index=0)
    baseline_file_path = test_pages_dir / selected_baseline

run_audit_clicked = st.sidebar.button("⚡ Run WCAG & UI Audit", type="primary", use_container_width=True)


# =========================================================================
# Session State & Audit Execution
# =========================================================================
if "current_result" not in st.session_state:
    st.session_state["current_result"] = None
if "regression_result" not in st.session_state:
    st.session_state["regression_result"] = None
if "triage_map" not in st.session_state:
    st.session_state["triage_map"] = {}


if run_audit_clicked and target_file_path:
    with st.spinner(f"Rendering {target_file_name} in Playwright & calculating 10 WCAG rules..."):
        # Audit target file
        audit_res = audit_page_file(target_file_path)
        st.session_state["current_result"] = audit_res

        # Initialize/preserve triage decisions
        t_map = {}
        for idx, v in enumerate(audit_res.violations):
            t_map[idx] = {
                "status": v.triage_status.value,
                "notes": v.reviewer_notes or "",
            }
        st.session_state["triage_map"] = t_map

        # Optional Regression Diff
        if enable_regression and baseline_file_path:
            with st.spinner("Diffing layout geometry & bounding boxes against baseline..."):
                reg_report = compare_page_snapshots(baseline_file_path, target_file_path)
                st.session_state["regression_result"] = reg_report
        else:
            st.session_state["regression_result"] = None

elif run_audit_clicked and not target_file_path:
    st.sidebar.warning("Please provide an HTML input source.")


# =========================================================================
# Main Dashboard UI
# =========================================================================
st.markdown('<div class="main-header">♿ AI Accessibility & UI Regression Auditor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Interactive QA Triage Suite &bull; 10-Rule Playwright Runtime &bull; Context-Aware LLM Remediation</div>', unsafe_allow_html=True)

res: PageAuditResult = st.session_state.get("current_result")

if not res:
    # Welcome Hero Screen
    st.info("👋 **Welcome to the Day-3 Streamlit QA Dashboard.** Select a test document from the left sidebar and click **'⚡ Run WCAG & UI Audit'** to begin.")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("#### 1. 10-Rule Playwright Engine")
        st.caption("Extracts real computed CSS contrast ratios, heading hierarchies, document language, ARIA bindings, and Tab-order keyboard simulation.")
    with col_b:
        st.markdown("#### 2. Human QA Triage Controls")
        st.caption("Reviewers can classify findings as Confirmed Defect, False Positive, or Won't Fix with reviewer commentary.")
    with col_c:
        st.markdown("#### 3. Multi-Format Exports")
        st.caption("Instant one-click exports to executive HTML, GitHub/Jira Markdown, and structured flat CSV tables.")

    st.markdown("---")
    st.markdown("##### 🚀 Quickstart: Try these seeded test pages")
    q_col1, q_col2, q_col3 = st.columns(3)
    if q_col1.button("Audit: 01_ecommerce_checkout.html", use_container_width=True):
        st.session_state["current_result"] = audit_page_file(test_pages_dir / "01_ecommerce_checkout.html")
        st.session_state["triage_map"] = {i: {"status": v.triage_status.value, "notes": v.reviewer_notes} for i, v in enumerate(st.session_state["current_result"].violations)}
        st.rerun()
    if q_col2.button("Audit: 02_saas_dashboard.html", use_container_width=True):
        st.session_state["current_result"] = audit_page_file(test_pages_dir / "02_saas_dashboard.html")
        st.session_state["triage_map"] = {i: {"status": v.triage_status.value, "notes": v.reviewer_notes} for i, v in enumerate(st.session_state["current_result"].violations)}
        st.rerun()
    if q_col3.button("Audit: 05_accessible_reference.html", use_container_width=True):
        st.session_state["current_result"] = audit_page_file(test_pages_dir / "05_accessible_reference.html")
        st.session_state["triage_map"] = {}
        st.rerun()

else:
    # Sync triage state into the model
    t_map = st.session_state.get("triage_map", {})
    for idx, v in enumerate(res.violations):
        if idx in t_map:
            v.triage_status = TriageStatus(t_map[idx]["status"])
            v.reviewer_notes = t_map[idx]["notes"]

    # Calculate dynamic metrics
    compliance_score = res.calculate_compliance_score()
    score_color = "#16a34a" if compliance_score >= 85 else ("#d97706" if compliance_score >= 60 else "#dc2626")

    total_findings = len(res.violations)
    confirmed_defects = sum(1 for v in res.violations if v.triage_status == TriageStatus.CONFIRMED_DEFECT)
    false_positives = sum(1 for v in res.violations if v.triage_status == TriageStatus.FALSE_POSITIVE)
    wont_fix = sum(1 for v in res.violations if v.triage_status == TriageStatus.WONT_FIX)
    pending = sum(1 for v in res.violations if v.triage_status == TriageStatus.PENDING)
    critical_serious = sum(1 for v in res.violations if v.severity in [Severity.CRITICAL, Severity.SERIOUS] and v.triage_status != TriageStatus.FALSE_POSITIVE)

    # Top KPI Metrics Row
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns([1.2, 1, 1, 1, 1])

    with kpi_col1:
        st.markdown(f"""
        <div class="score-box" style="border-color: {score_color};">
          <div class="score-number" style="color: {score_color};">{compliance_score}%</div>
          <div class="score-caption">WCAG 2.1 AA Compliance<br><span style="font-size:0.6rem; color:#94a3b8;">(Excludes False Positives)</span></div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        st.metric("Total Findings", total_findings, help="All automated WCAG barriers detected")
    with kpi_col3:
        st.metric("Confirmed Defects", confirmed_defects, delta=f"-{confirmed_defects}" if confirmed_defects else None, delta_color="inverse")
    with kpi_col4:
        st.metric("Critical & Serious", critical_serious, help="High priority accessibility blockers")
    with kpi_col5:
        st.metric("False Positives", false_positives, delta=f"+{false_positives}" if false_positives else None, delta_color="normal")

    # One-Click Multi-Format Export Bar
    st.markdown("#### 📥 One-Click QA Report Exports")
    exp_col1, exp_col2, exp_col3 = st.columns(3)

    with exp_col1:
        html_data = export_to_html(res)
        st.download_button(
            label="📄 Download Executive HTML Report",
            data=html_data,
            file_name=f"qa_report_{res.page_name}.html",
            mime="text/html",
            use_container_width=True,
        )

    with exp_col2:
        md_data = export_to_markdown(res)
        st.download_button(
            label="📝 Download GitHub/Jira Markdown",
            data=md_data,
            file_name=f"qa_report_{res.page_name}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with exp_col3:
        csv_data = export_to_csv(res)
        st.download_button(
            label="📊 Download Flat CSV Data",
            data=csv_data,
            file_name=f"qa_report_{res.page_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")

    # Main Tabs
    reg_report: RegressionDiffReport = st.session_state.get("regression_result")
    tab_labels = [f"♿ Accessibility Findings ({total_findings})", "🖥️ Live Document Preview"]
    if reg_report:
        tab_labels.insert(1, f"📐 Layout Regression ({reg_report.total_layout_shifts} shifts)")

    tabs = st.tabs(tab_labels)

    # ---------------------------------------------------------------------
    # TAB 1: Accessibility Findings with Triage & Code Diffs
    # ---------------------------------------------------------------------
    with tabs[0]:
        # Filter Bar
        f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
        with f_col1:
            severity_filter = st.selectbox(
                "Filter by Severity:",
                ["All", "Critical", "Serious", "Moderate", "Minor"],
                index=0,
            )
        with f_col2:
            triage_filter = st.selectbox(
                "Filter by QA Triage Status:",
                ["All", "Pending", "Confirmed Defect", "False Positive", "Won't Fix"],
                index=0,
            )
        with f_col3:
            search_query = st.text_input("🔍 Search rule, selector, or text:", placeholder="Type selector or keyword...").strip().lower()

        # Filter violations
        filtered_violations = []
        for idx, v in enumerate(res.violations):
            matches_sev = (severity_filter == "All") or (v.severity.value == severity_filter)
            matches_triage = (triage_filter == "All") or (v.triage_status.value == triage_filter)
            matches_search = (
                not search_query
                or search_query in v.rule_id.lower()
                or search_query in v.rule_name.lower()
                or search_query in v.dom_selector.lower()
                or search_query in v.issue_explanation.lower()
            )
            if matches_sev and matches_triage and matches_search:
                filtered_violations.append((idx, v))

        st.caption(f"Showing {len(filtered_violations)} of {total_findings} findings matching filters.")

        if not filtered_violations and total_findings > 0:
            st.info("No findings match the selected filter criteria.")

        elif total_findings == 0:
            st.success("🎉 **100% WCAG 2.1 AA Compliant!** Zero accessibility barriers detected across all 10 rules.")

        # Render filtered issue cards
        for idx, v in filtered_violations:
            with st.container(border=True):
                # Header row: Rule ID, severity, triage badge
                h_col1, h_col2 = st.columns([3, 1])
                with h_col1:
                    st.markdown(f"### #{idx+1} &bull; {v.rule_name} (`{v.rule_id}`)")
                    st.markdown(f"**Target DOM Selector:** <span class='selector-chip'>{v.dom_selector}</span>", unsafe_allow_html=True)
                with h_col2:
                    sev_badge = "badge-crit" if v.severity == Severity.CRITICAL else ("badge-ser" if v.severity == Severity.SERIOUS else "badge-mod")
                    st.markdown(f"<span class='{sev_badge}'>{v.severity.value}</span>", unsafe_allow_html=True)

                st.write(v.issue_explanation)

                # Human QA Triage Controls
                st.markdown("##### 🕵️ Human QA Triage Review")
                t_col1, t_col2 = st.columns([1, 2])

                triage_options = ["Pending", "Confirmed Defect", "False Positive", "Won't Fix"]
                current_status_idx = triage_options.index(v.triage_status.value) if v.triage_status.value in triage_options else 0

                with t_col1:
                    new_status = st.selectbox(
                        "QA Status:",
                        options=triage_options,
                        index=current_status_idx,
                        key=f"status_select_{idx}",
                    )
                with t_col2:
                    new_notes = st.text_input(
                        "Reviewer Notes / Commentary:",
                        value=v.reviewer_notes or "",
                        key=f"notes_input_{idx}",
                        placeholder="Add QA investigation notes or ticket reference...",
                    )

                # If triage values updated, sync to session state
                if new_status != v.triage_status.value or new_notes != v.reviewer_notes:
                    st.session_state["triage_map"][idx] = {
                        "status": new_status,
                        "notes": new_notes,
                    }
                    st.rerun()

                # Side-by-Side Before & After HTML Code Diff
                st.markdown("##### 🔄 Remediation Patch (Before & After Diff)")
                diff_c1, diff_c2 = st.columns(2)

                with diff_c1:
                    st.markdown("**🔴 Original Non-Compliant HTML**")
                    st.code(v.before_html or v.raw_html_snippet, language="html")

                with diff_c2:
                    st.markdown("**🟢 Recommended Accessible Patch** *(One-click copy icon on top-right)*")
                    st.code(v.after_html or v.suggested_fix, language="html")

    # ---------------------------------------------------------------------
    # TAB 2: Optional Visual Layout Regression Diff
    # ---------------------------------------------------------------------
    if reg_report:
        with tabs[1]:
            st.markdown(f"### 📐 Visual Layout & DOM Regression Diff Report")
            st.caption(f"Comparing `{reg_report.baseline_page}` (Baseline) vs `{reg_report.modified_page}` (Modified)")

            r_col1, r_col2, r_col3 = st.columns(3)
            r_col1.metric("Layout Shifts", reg_report.total_layout_shifts)
            r_col2.metric("Style Mutations", reg_report.total_style_regressions)
            r_col3.metric("Structural Changes", reg_report.total_structural_changes)

            st.markdown("#### Detected Bounding Box Shifts")
            if reg_report.layout_shifts:
                shift_table = []
                for s in reg_report.layout_shifts:
                    shift_table.append({
                        "DOM Selector": s.dom_selector,
                        "Delta X (px)": s.delta_x,
                        "Delta Y (px)": s.delta_y,
                        "Delta Width (px)": s.delta_width,
                        "Delta Height (px)": s.delta_height,
                        "Description": s.shift_description,
                    })
                st.dataframe(shift_table, use_container_width=True)
            else:
                st.success("No geometric layout shifts exceeding threshold detected.")

            st.markdown("#### Structural DOM Mutations")
            st.write(f"- **Added Elements:** {len(reg_report.structural_changes.added_elements)}")
            for a in reg_report.structural_changes.added_elements[:5]:
                st.caption(f"  + `{a}`")
            st.write(f"- **Removed Elements:** {len(reg_report.structural_changes.removed_elements)}")
            for rm in reg_report.structural_changes.removed_elements[:5]:
                st.caption(f"  - `{rm}`")

    # ---------------------------------------------------------------------
    # TAB 3 / 2: Live Document Preview
    # ---------------------------------------------------------------------
    preview_tab_index = 2 if reg_report else 1
    with tabs[preview_tab_index]:
        st.markdown("### 🖥️ Rendered Document Preview")
        target_path = Path(res.file_path)
        if target_path.exists():
            html_raw = target_path.read_text(encoding="utf-8")
            components.html(html_raw, height=600, scrolling=True)
        else:
            st.warning("Preview not available for this source.")
