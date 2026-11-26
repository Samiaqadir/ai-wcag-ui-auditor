"""
DOM Parser and Playwright Runtime Style/Geometry Extraction Engine.
Renders pages in headless Chromium via Playwright to extract real computed CSS styles,
bounding boxes (getBoundingClientRect), and keyboard Tab sequence simulation.
Includes graceful fallback for static parsing when headless rendering is unavailable.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from bs4 import BeautifulSoup, Tag

from auditor.models import BoundingBox


def generate_css_selector(tag: Tag) -> str:
    """
    Constructs a unique, verifiable CSS selector for any BeautifulSoup Tag.
    Prioritizes IDs, unique classes, and hierarchical :nth-of-type paths.
    """
    if not tag or not hasattr(tag, "name") or tag.name in ["[document]", "html", "body"]:
        return tag.name if hasattr(tag, "name") and tag.name else "body"

    tag_id = tag.get("id")
    if tag_id and isinstance(tag_id, str) and not re.search(r"\s", tag_id):
        return f"#{tag_id}"

    path = []
    current = tag
    while current and current.name and current.name != "[document]":
        segment = current.name
        curr_id = current.get("id")
        if curr_id and isinstance(curr_id, str) and not re.search(r"\s", curr_id):
            segment = f"#{curr_id}"
            path.append(segment)
            break

        classes = current.get("class", [])
        if classes:
            class_str = ".".join(classes[:2])
            segment = f"{current.name}.{class_str}"

        parent = current.parent
        if parent:
            siblings = [s for s in parent.children if isinstance(s, Tag) and s.name == current.name]
            if len(siblings) > 1:
                idx = siblings.index(current) + 1
                segment = f"{segment}:nth-of-type({idx})"

        path.append(segment)
        if current.name in ["body", "main", "header", "footer", "form", "article"]:
            break
        current = current.parent

    return " > ".join(reversed(path))


class ElementRuntimeData:
    """Stores computed styles and geometric layout information for an element."""
    def __init__(
        self,
        selector: str,
        tag_name: str,
        styles: Dict[str, str],
        bounding_box: BoundingBox,
        raw_html: str,
        text_content: str,
        attributes: Dict[str, Any],
        is_visible: bool = True,
    ):
        self.selector = selector
        self.tag_name = tag_name
        self.styles = styles
        self.bounding_box = bounding_box
        self.raw_html = raw_html
        self.text_content = text_content
        self.attributes = attributes
        self.is_visible = is_visible


class PageInspectionResult:
    """Aggregated runtime inspection data returned by PlaywrightDOMInspector."""
    def __init__(
        self,
        file_path: str,
        html_content: str,
        soup: BeautifulSoup,
        elements: Dict[str, ElementRuntimeData],
        tab_sequence: List[str],
        unreachable_interactive: List[str],
        playwright_active: bool = True,
    ):
        self.file_path = file_path
        self.html_content = html_content
        self.soup = soup
        self.elements = elements
        self.tab_sequence = tab_sequence
        self.unreachable_interactive = unreachable_interactive
        self.playwright_active = playwright_active


class PlaywrightDOMInspector:
    """
    Renders documents in headless Chromium using Playwright to extract real
    computed styles, layout bounding boxes, and simulated keyboard tab navigation.
    """

    @classmethod
    def inspect(cls, file_path: Path | str) -> PageInspectionResult:
        path = Path(file_path).resolve()
        html_content = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "html.parser")

        elements_map: Dict[str, ElementRuntimeData] = {}
        tab_sequence: List[str] = []
        unreachable_interactive: List[str] = []
        playwright_succeeded = False

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(path.as_uri(), wait_until="load")

                # In-browser JS extraction script
                extraction_js = """
                () => {
                    const data = [];
                    const allElements = document.querySelectorAll('*');

                    function getEffectiveBackground(el) {
                        let cur = el;
                        while (cur && cur !== document) {
                            const style = window.getComputedStyle(cur);
                            const bg = style.backgroundColor;
                            if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
                                return bg;
                            }
                            cur = cur.parentElement;
                        }
                        return 'rgb(255, 255, 255)';
                    }

                    function getUniqueSelector(el) {
                        if (el.id) return '#' + CSS.escape(el.id);
                        if (el === document.body) return 'body';
                        if (el === document.documentElement) return 'html';
                        
                        let path = [];
                        let cur = el;
                        while (cur && cur !== document.body && cur !== document.documentElement) {
                            let seg = cur.tagName.toLowerCase();
                            if (cur.className && typeof cur.className === 'string') {
                                const cls = cur.className.trim().split(/\\s+/)[0];
                                if (cls) seg += '.' + CSS.escape(cls);
                            }
                            if (cur.parentElement) {
                                const siblings = Array.from(cur.parentElement.children).filter(s => s.tagName === cur.tagName);
                                if (siblings.length > 1) {
                                    seg += `:nth-of-type(${siblings.indexOf(cur) + 1})`;
                                }
                            }
                            path.unshift(seg);
                            cur = cur.parentElement;
                        }
                        return path.join(' > ');
                    }

                    allElements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        const selector = getUniqueSelector(el);
                        
                        // Extract attributes
                        const attrs = {};
                        for (let attr of el.attributes) {
                            attrs[attr.name] = attr.value;
                        }

                        // Check true visual visibility across ancestor cascades and inert templates
                        let isVisible = true;
                        if (el.closest('template') || el.closest('[aria-hidden="true"]')) {
                            isVisible = false;
                        } else if (typeof el.checkVisibility === 'function') {
                            isVisible = el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
                        } else {
                            isVisible = (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0');
                        }
                        if (rect.width <= 0 || rect.height <= 0) {
                            isVisible = false;
                        }

                        data.push({
                            selector: selector,
                            tag: el.tagName.toLowerCase(),
                            raw_html: el.outerHTML.slice(0, 300),
                            text: el.innerText || el.textContent || '',
                            attributes: attrs,
                            is_visible: isVisible,
                            rect: {
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            },
                            styles: {
                                color: style.color,
                                backgroundColor: getEffectiveBackground(el),
                                rawBackgroundColor: style.backgroundColor,
                                fontSize: style.fontSize,
                                fontWeight: style.fontWeight,
                                outlineStyle: style.outlineStyle,
                                outlineWidth: style.outlineWidth,
                                outlineColor: style.outlineColor,
                                display: style.display,
                                visibility: style.visibility,
                                opacity: style.opacity
                            }
                        });
                    });

                    return data;
                }
                """
                raw_extracted = page.evaluate(extraction_js)

                for item in raw_extracted:
                    sel = item["selector"]
                    bbox = BoundingBox(
                        x=round(item["rect"]["x"], 2),
                        y=round(item["rect"]["y"], 2),
                        width=round(item["rect"]["width"], 2),
                        height=round(item["rect"]["height"], 2),
                    )
                    elements_map[sel] = ElementRuntimeData(
                        selector=sel,
                        tag_name=item["tag"],
                        styles=item["styles"],
                        bounding_box=bbox,
                        raw_html=item["raw_html"],
                        text_content=item["text"],
                        attributes=item["attributes"],
                        is_visible=item.get("is_visible", True),
                    )

                # Simulate sequential Tab keyboard navigation
                # Focus body first, then press Tab repeatedly
                page.focus("body")
                for _ in range(25):
                    page.keyboard.press("Tab")
                    active_sel = page.evaluate("""() => {
                        const el = document.activeElement;
                        if (!el || el === document.body) return null;
                        if (el.id) return '#' + el.id;
                        return el.tagName.toLowerCase() + (el.className ? '.' + el.className.trim().split(/\\s+/)[0] : '');
                    }""")
                    if active_sel and (not tab_sequence or tab_sequence[-1] != active_sel):
                        tab_sequence.append(active_sel)

                # Check interactive elements (buttons, inputs, links, [role=button])
                interactive_selectors = page.evaluate("""() => {
                    const sel = [];
                    document.querySelectorAll('button, a[href], input:not([type="hidden"]), select, textarea, [role="button"]').forEach(el => {
                        sel.push(el.id ? '#' + el.id : el.tagName.toLowerCase());
                    });
                    return sel;
                }""")

                # Identify interactive elements that could not be reached via Tab
                for i_sel in interactive_selectors:
                    if not any(i_sel in t for t in tab_sequence):
                        unreachable_interactive.append(i_sel)

                browser.close()
                playwright_succeeded = True

        except Exception as e:
            # Fallback static resolution if Playwright has runtime issue
            playwright_succeeded = False

        if not playwright_succeeded or not elements_map:
            # Static fallback parser
            elements_map = cls._build_static_elements_map(soup)

        return PageInspectionResult(
            file_path=str(path),
            html_content=html_content,
            soup=soup,
            elements=elements_map,
            tab_sequence=tab_sequence,
            unreachable_interactive=unreachable_interactive,
            playwright_active=playwright_succeeded,
        )

    @classmethod
    def _build_static_elements_map(cls, soup: BeautifulSoup) -> Dict[str, ElementRuntimeData]:
        """Fallback static extractor when Playwright headless browser is offline."""
        elements_map = {}
        for tag in soup.find_all(True):
            selector = generate_css_selector(tag)
            attrs = {k: v if isinstance(v, str) else " ".join(v) for k, v in tag.attrs.items()}
            raw = str(tag)[:300]
            text = tag.get_text(strip=True)

            elements_map[selector] = ElementRuntimeData(
                selector=selector,
                tag_name=tag.name,
                styles={
                    "color": "#000000",
                    "backgroundColor": "#ffffff",
                    "fontSize": "16px",
                    "fontWeight": "400",
                    "outlineStyle": "auto",
                    "outlineWidth": "1px",
                    "outlineColor": "#000000",
                    "display": "block",
                    "visibility": "visible",
                    "opacity": "1",
                },
                bounding_box=BoundingBox(x=0, y=0, width=100, height=30),
                raw_html=raw,
                text_content=text,
                attributes=attrs,
            )
        return elements_map
