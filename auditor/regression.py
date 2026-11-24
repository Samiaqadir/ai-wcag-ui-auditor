"""
Visual Layout & DOM Regression Diffing Engine.
Renders baseline and modified HTML documents in Playwright to detect:
1. Bounding box geometric layout shifts (position delta_x/delta_y, dimension delta_w/delta_h)
2. Computed CSS style regressions (color, background, font-size, display)
3. Structural DOM mutations (added and removed elements)
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone

from auditor.models import (
    BoundingBox,
    LayoutShift,
    StyleRegression,
    StructuralDiff,
    RegressionDiffReport,
)
from auditor.parser import PlaywrightDOMInspector, PageInspectionResult


def compare_page_snapshots(
    baseline_path: Path | str,
    modified_path: Path | str,
    shift_threshold_px: float = 4.0,
) -> RegressionDiffReport:
    """
    Renders both baseline and modified pages, extracting runtime bounding boxes
    and computed styles to detect layout shifts and UI regressions.
    """
    base_p = Path(baseline_path).resolve()
    mod_p = Path(modified_path).resolve()

    base_insp = PlaywrightDOMInspector.inspect(base_p)
    mod_insp = PlaywrightDOMInspector.inspect(mod_p)

    base_elements = base_insp.elements
    mod_elements = mod_insp.elements

    # 1. Structural DOM Changes
    base_selectors = set(base_elements.keys())
    mod_selectors = set(mod_elements.keys())

    removed = sorted(list(base_selectors - mod_selectors))
    added = sorted(list(mod_selectors - base_selectors))
    common = sorted(list(base_selectors & mod_selectors))

    structural_diff = StructuralDiff(
        added_elements=added,
        removed_elements=removed,
    )

    # 2. Geometric Layout Shifts (Bounding Box diffs)
    layout_shifts: List[LayoutShift] = []

    for sel in common:
        b_box = base_elements[sel].bounding_box
        m_box = mod_elements[sel].bounding_box

        # Skip elements that are hidden or zero-dimension in both
        if (b_box.width == 0 and b_box.height == 0) and (m_box.width == 0 and m_box.height == 0):
            continue

        dx = round(m_box.x - b_box.x, 2)
        dy = round(m_box.y - b_box.y, 2)
        dw = round(m_box.width - b_box.width, 2)
        dh = round(m_box.height - b_box.height, 2)

        has_position_shift = abs(dx) >= shift_threshold_px or abs(dy) >= shift_threshold_px
        has_dimension_shift = abs(dw) >= shift_threshold_px or abs(dh) >= shift_threshold_px

        if has_position_shift or has_dimension_shift:
            desc_parts = []
            if abs(dx) >= shift_threshold_px:
                dir_x = "right" if dx > 0 else "left"
                desc_parts.append(f"shifted {dir_x} by {abs(dx)}px")
            if abs(dy) >= shift_threshold_px:
                dir_y = "down" if dy > 0 else "up"
                desc_parts.append(f"shifted {dir_y} by {abs(dy)}px")
            if abs(dw) >= shift_threshold_px:
                sign_w = "expanded" if dw > 0 else "shrunk"
                desc_parts.append(f"width {sign_w} by {abs(dw)}px")
            if abs(dh) >= shift_threshold_px:
                sign_h = "expanded" if dh > 0 else "shrunk"
                desc_parts.append(f"height {sign_h} by {abs(dh)}px")

            description = f"Layout Shift: {', '.join(desc_parts)}"

            layout_shifts.append(
                LayoutShift(
                    dom_selector=sel,
                    baseline_box=b_box,
                    modified_box=m_box,
                    delta_x=dx,
                    delta_y=dy,
                    delta_width=dw,
                    delta_height=dh,
                    shift_description=description,
                )
            )

    # 3. Computed Style Regressions
    style_regressions: List[StyleRegression] = []
    monitored_props = ["color", "backgroundColor", "fontSize", "display", "visibility"]

    for sel in common:
        b_styles = base_elements[sel].styles
        m_styles = mod_elements[sel].styles

        for prop in monitored_props:
            b_val = b_styles.get(prop, "").strip().lower()
            m_val = m_styles.get(prop, "").strip().lower()

            if b_val and m_val and b_val != m_val:
                impact = f"Computed style '{prop}' changed from '{b_val}' to '{m_val}'"
                if prop in ["color", "backgroundColor"]:
                    impact += " (Potential WCAG contrast impact)"

                style_regressions.append(
                    StyleRegression(
                        dom_selector=sel,
                        property_name=prop,
                        baseline_value=b_val,
                        modified_value=m_val,
                        impact=impact,
                    )
                )

    summary = (
        f"Regression Diff: {len(layout_shifts)} layout shifts, "
        f"{len(style_regressions)} style mutations, "
        f"{len(added)} added elements, {len(removed)} removed elements."
    )

    return RegressionDiffReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        baseline_page=base_p.name,
        modified_page=mod_p.name,
        total_layout_shifts=len(layout_shifts),
        total_style_regressions=len(style_regressions),
        total_structural_changes=len(added) + len(removed),
        layout_shifts=layout_shifts,
        style_regressions=style_regressions,
        structural_changes=structural_diff,
        summary=summary,
    )
