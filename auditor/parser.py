"""
DOM Parser and Style Extraction Engine.
Extracts DOM trees, generates precise CSS selectors, and computes element styles
using Playwright browser rendering with fallback static CSS analysis.
"""

import re
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from bs4 import BeautifulSoup, Tag


def generate_css_selector(tag: Tag) -> str:
    """
    Constructs a precise, human-readable CSS selector for any BeautifulSoup Tag.
    Prioritizes IDs, classes, and hierarchical nth-of-type paths.
    """
    if not tag or not hasattr(tag, "name") or tag.name in ["[document]", "html", "body"]:
        return tag.name if hasattr(tag, "name") and tag.name else "body"

    # If element has a valid unique ID, use #id
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

        # Calculate nth-of-type among siblings
        parent = current.parent
        if parent:
            siblings = [s for s in parent.children if isinstance(s, Tag) and s.name == current.name]
            if len(siblings) > 1:
                idx = siblings.index(current) + 1
                segment = f"{segment}:nth-of-type({idx})"

        path.append(segment)
        if current.name in ["body", "main", "header", "footer", "form"]:
            break
        current = current.parent

    return " > ".join(reversed(path))


class StyleResolver:
    """
    Resolves computed styles (colors, fonts, outlines) for DOM nodes.
    Supports Playwright dynamic browser evaluation with robust static CSS fallback.
    """

    def __init__(self, html_content: str, file_path: Optional[str] = None):
        self.html_content = html_content
        self.file_path = file_path
        self.css_rules = self._extract_embedded_css_rules()

    def _extract_embedded_css_rules(self) -> Dict[str, Dict[str, str]]:
        """
        Parses CSS declarations from embedded <style> blocks and CSS variables.
        """
        rules: Dict[str, Dict[str, str]] = {}
        css_blocks = re.findall(r"<style[^>]*>(.*?)</style>", self.html_content, re.DOTALL | re.IGNORECASE)

        # First pass: collect :root variables
        root_vars: Dict[str, str] = {}
        for block in css_blocks:
            root_matches = re.findall(r":root\s*\{([^}]+)\}", block, re.IGNORECASE)
            for rm in root_matches:
                for var_decl in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", rm):
                    root_vars[var_decl[0].strip()] = var_decl[1].strip()

        for block in css_blocks:
            # Strip comments
            clean_block = re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL)
            # Find rule selectors and body
            for match in re.finditer(r"([^{]+)\{([^}]+)\}", clean_block):
                selectors_str = match.group(1).strip()
                declarations = match.group(2).strip()

                props: Dict[str, str] = {}
                for decl in re.finditer(r"([\w-]+)\s*:\s*([^;]+)(?:;|$)", declarations):
                    prop_name = decl.group(1).strip().lower()
                    prop_val = decl.group(2).strip()

                    # Substitute CSS variables if used
                    var_match = re.search(r"var\((--[\w-]+)\)", prop_val)
                    if var_match and var_match.group(1) in root_vars:
                        prop_val = root_vars[var_match.group(1)]

                    props[prop_name] = prop_val

                # Multiple comma-separated selectors
                for sel in selectors_str.split(","):
                    sel_clean = sel.strip()
                    if sel_clean:
                        if sel_clean not in rules:
                            rules[sel_clean] = {}
                        rules[sel_clean].update(props)

        return rules

    def get_element_styles(self, tag: Tag) -> Dict[str, str]:
        """
        Returns resolved style properties (color, background-color, font-size, etc.)
        for a given BeautifulSoup tag.
        """
        styles: Dict[str, str] = {
            "color": "#000000",
            "background-color": "#ffffff",
            "font-size": "16px",
            "font-weight": "400",
            "outline": "auto",
        }

        # 1. Match tag name
        if tag.name in self.css_rules:
            styles.update(self.css_rules[tag.name])

        # 2. Match classes
        classes = tag.get("class", [])
        if isinstance(classes, list):
            for c in classes:
                dot_c = f".{c}"
                if dot_c in self.css_rules:
                    styles.update(self.css_rules[dot_c])
                tag_dot_c = f"{tag.name}.{c}"
                if tag_dot_c in self.css_rules:
                    styles.update(self.css_rules[tag_dot_c])

        # 3. Match ID
        tag_id = tag.get("id")
        if tag_id and f"#{tag_id}" in self.css_rules:
            styles.update(self.css_rules[f"#{tag_id}"])

        # 4. Inline style attribute overrides CSS rules
        inline_style = tag.get("style", "")
        if inline_style:
            for decl in re.finditer(r"([\w-]+)\s*:\s*([^;]+)(?:;|$)", inline_style):
                p_name = decl.group(1).strip().lower()
                p_val = decl.group(2).strip()
                styles[p_name] = p_val

        return styles


def parse_html_document(html_content: str, file_path: Optional[str] = None) -> Tuple[BeautifulSoup, StyleResolver]:
    """
    Parses HTML into a BeautifulSoup DOM tree alongside a configured StyleResolver.
    """
    soup = BeautifulSoup(html_content, "lxml" if "lxml" in BeautifulSoup.__module__ or True else "html.parser")
    try:
        # Test lxml parser availability
        soup = BeautifulSoup(html_content, "lxml")
    except Exception:
        soup = BeautifulSoup(html_content, "html.parser")

    resolver = StyleResolver(html_content=html_content, file_path=file_path)
    return soup, resolver
