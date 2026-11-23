"""
WCAG 2.1 AA Relative Luminance & Color Contrast Calculator.
Implements the exact formulas defined by W3C WCAG 2.1 Criterion 1.4.3.
"""

import re
from typing import Tuple, Dict, Optional


NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "purple": (128, 0, 128),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "transparent": (255, 255, 255),
}


def parse_color(color_str: str, default: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    """
    Parses various CSS color representations (hex, rgb, rgba, named colors)
    into an (R, G, B) integer tuple [0..255].
    """
    if not color_str:
        return default

    clean_str = color_str.strip().lower()

    # Named color lookup
    if clean_str in NAMED_COLORS:
        return NAMED_COLORS[clean_str]

    # Hex: #RGB
    if re.match(r"^#[0-9a-f]{3}$", clean_str):
        r = int(clean_str[1] * 2, 16)
        g = int(clean_str[2] * 2, 16)
        b = int(clean_str[3] * 2, 16)
        return (r, g, b)

    # Hex: #RRGGBB
    if re.match(r"^#[0-9a-f]{6}$", clean_str):
        r = int(clean_str[1:3], 16)
        g = int(clean_str[3:5], 16)
        b = int(clean_str[5:7], 16)
        return (r, g, b)

    # Hex: #RRGGBBAA
    if re.match(r"^#[0-9a-f]{8}$", clean_str):
        r = int(clean_str[1:3], 16)
        g = int(clean_str[3:5], 16)
        b = int(clean_str[5:7], 16)
        return (r, g, b)

    # rgb(r, g, b)
    rgb_match = re.match(r"^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$", clean_str)
    if rgb_match:
        return (
            min(255, max(0, int(rgb_match.group(1)))),
            min(255, max(0, int(rgb_match.group(2)))),
            min(255, max(0, int(rgb_match.group(3)))),
        )

    # rgba(r, g, b, a)
    rgba_match = re.match(r"^rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([\d\.]+)\s*\)$", clean_str)
    if rgba_match:
        r = min(255, max(0, int(rgba_match.group(1))))
        g = min(255, max(0, int(rgba_match.group(2))))
        b = min(255, max(0, int(rgba_match.group(3))))
        alpha = float(rgba_match.group(4))
        # Simple composite against white background
        r = int(r * alpha + 255 * (1 - alpha))
        g = int(g * alpha + 255 * (1 - alpha))
        b = int(b * alpha + 255 * (1 - alpha))
        return (r, g, b)

    return default


def calculate_luminance(r: int, g: int, b: int) -> float:
    """
    Computes WCAG 2.1 relative luminance for an sRGB color.
    Formula:
      R_srgb = R / 255
      R_lin = R_srgb / 12.92 if R_srgb <= 0.04045 else ((R_srgb + 0.055) / 1.055) ** 2.4
      L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin
    """
    def channel_linear(val: int) -> float:
        c = val / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = channel_linear(r)
    g_lin = channel_linear(g)
    b_lin = channel_linear(b)

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calculate_contrast_ratio(color1: str | Tuple[int, int, int], color2: str | Tuple[int, int, int]) -> float:
    """
    Calculates the WCAG contrast ratio between two colors:
      CR = (L1 + 0.05) / (L2 + 0.05)
    where L1 is the relative luminance of the lighter color, and L2 is the darker.
    Returns a float rounded to 2 decimal places (e.g. 4.54).
    """
    c1 = parse_color(color1, default=(0, 0, 0)) if isinstance(color1, str) else color1
    c2 = parse_color(color2, default=(255, 255, 255)) if isinstance(color2, str) else color2

    lum1 = calculate_luminance(*c1)
    lum2 = calculate_luminance(*c2)

    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)

    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, 2)


def is_contrast_compliant(
    fg_color: str | Tuple[int, int, int],
    bg_color: str | Tuple[int, int, int],
    is_large_text: bool = False,
    level: str = "AA",
) -> Tuple[bool, float, float]:
    """
    Verifies if color combination satisfies WCAG minimum contrast threshold.
    Returns: (is_compliant, calculated_ratio, required_threshold)
    """
    ratio = calculate_contrast_ratio(fg_color, bg_color)

    if level.upper() == "AAA":
        threshold = 4.5 if is_large_text else 7.0
    else:  # Default to AA
        threshold = 3.0 if is_large_text else 4.5

    return (ratio >= threshold, ratio, threshold)
