"""charts plugin — render simple bar/line PNGs for the Advisor to send.

The Advisor gathers numbers (via delegated Accountant/Analyst), then calls these
tools to turn them into a clean image. Each tool returns a file path; the Advisor
embeds it as ``MEDIA:<path>`` in its reply and the platform delivers it as a
native image (one MEDIA line = one image message).

Pure PIL (matplotlib is not installed). Charts are deliberately minimal: title,
labelled bars/points, value labels. Palette matches the Tallyzen docs.
"""

from __future__ import annotations

import logging
import os
import time

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

OUT_DIR = os.path.expanduser("~/.hermes/cache/tallyzen-charts")
W = 1000
PALETTE = ["#1f7a55", "#1f6f8b", "#d8a13e", "#5aa982", "#b07d16", "#7a8579"]
INK = "#182b23"
MUTED = "#55645a"
GRID = "#e2d8c1"
BG = "#fffdf7"

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # has the ₹ glyph
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/SFNS.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size):
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _text_w(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _ensure_dir():
    os.makedirs(OUT_DIR, exist_ok=True)


def _new_path(kind):
    _ensure_dir()
    return os.path.join(OUT_DIR, kind + "-" + str(int(time.time() * 1000)) + ".png")


def _fmt(value, prefix):
    v = float(value)
    if abs(v) >= 1e7:
        return prefix + str(round(v / 1e7, 2)) + " Cr"
    if abs(v) >= 1e5:
        return prefix + str(round(v / 1e5, 2)) + " L"
    return prefix + format(int(v), ",")


def render_bar(title, categories, values, value_prefix="Rs ", subtitle=""):
    n = max(1, len(values))
    row_h, top, left, right, bottom = 62, 130, 240, 60, 70
    height = top + n * row_h + bottom
    img = Image.new("RGB", (W, height), _hex(BG))
    d = ImageDraw.Draw(img)
    d.text((50, 40), title, fill=_hex(INK), font=_font(34))
    if subtitle:
        d.text((50, 84), subtitle, fill=_hex(MUTED), font=_font(20))
    max_v = max([abs(float(v)) for v in values] + [1])
    f_lab, f_val = _font(22), _font(20)
    # Reserve right-edge space so the longest bar's value label never clips.
    value_reserve = max([_text_w(d, _fmt(v, value_prefix), f_val) for v in values] + [80]) + 30
    bar_area = W - left - right - value_reserve
    for i, (cat, val) in enumerate(zip(categories, values)):
        y = top + i * row_h
        color = _hex(PALETTE[i % len(PALETTE)])
        d.text((50, y + 12), str(cat), fill=_hex(INK), font=f_lab)
        bar_w = int(bar_area * (abs(float(val)) / max_v))
        d.rounded_rectangle([left, y + 8, left + max(bar_w, 3), y + 44], radius=8, fill=color)
        d.text((left + max(bar_w, 3) + 12, y + 14), _fmt(val, value_prefix), fill=_hex(MUTED), font=f_val)
    path = _new_path("bar")
    img.save(path, "PNG")
    return path


def render_line(title, x_labels, values, value_prefix="Rs ", subtitle=""):
    left, right, top, bottom = 90, 60, 130, 90
    height = 560
    plot_w, plot_h = W - left - right, height - top - bottom
    img = Image.new("RGB", (W, height), _hex(BG))
    d = ImageDraw.Draw(img)
    d.text((50, 40), title, fill=_hex(INK), font=_font(34))
    if subtitle:
        d.text((50, 84), subtitle, fill=_hex(MUTED), font=_font(20))
    vals = [float(v) for v in values]
    max_v, n = max(vals + [1]), max(1, len(vals))
    for g in range(5):
        gy = top + plot_h - int(plot_h * g / 4)
        d.line([left, gy, W - right, gy], fill=_hex(GRID), width=1)
        d.text((left - 78, gy - 10), _fmt(max_v * g / 4, value_prefix), fill=_hex(MUTED), font=_font(16))
    step = plot_w / max(1, n - 1)
    pts = []
    for i, v in enumerate(vals):
        x = left + int(step * i)
        y = top + plot_h - int(plot_h * (v / max_v))
        pts.append((x, y))
    if len(pts) > 1:
        d.line(pts, fill=_hex(PALETTE[0]), width=4, joint="curve")
    f_x = _font(18)
    for i, (x, y) in enumerate(pts):
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=_hex(PALETTE[0]))
        if i < len(x_labels):
            lab = str(x_labels[i])
            d.text((x - _text_w(d, lab, f_x) // 2, top + plot_h + 14), lab, fill=_hex(MUTED), font=f_x)
    path = _new_path("line")
    img.save(path, "PNG")
    return path


# --- handlers: (args, **kw) -> str (a MEDIA: line the Advisor puts in its reply) ---
def handle_chart_bar(args, **kw):
    try:
        path = render_bar(
            title=args.get("title", "Chart"),
            categories=args.get("categories", []),
            values=args.get("values", []),
            value_prefix=args.get("value_prefix", "Rs "),
            subtitle=args.get("subtitle", ""),
        )
        return "MEDIA:" + path
    except Exception as e:  # noqa: BLE001
        return '{"error": "chart render failed: ' + str(e).replace('"', "'") + '"}'


def handle_chart_line(args, **kw):
    try:
        path = render_line(
            title=args.get("title", "Trend"),
            x_labels=args.get("x_labels", []),
            values=args.get("values", []),
            value_prefix=args.get("value_prefix", "Rs "),
            subtitle=args.get("subtitle", ""),
        )
        return "MEDIA:" + path
    except Exception as e:  # noqa: BLE001
        return '{"error": "chart render failed: ' + str(e).replace('"', "'") + '"}'


CHART_BAR_SCHEMA = {
    "name": "chart_bar",
    "description": "Render a horizontal bar chart PNG and return a 'MEDIA:<path>' string. Put that exact string in your reply on its own line and the platform sends it as an image. Use for comparisons like sales by country or by product line. categories and values must be the same length and same order.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Chart title."},
            "subtitle": {"type": "string", "description": "Optional one-line subtitle."},
            "categories": {"type": "array", "items": {"type": "string"}, "description": "Bar labels, e.g. ['USA','China','Vietnam','Others']."},
            "values": {"type": "array", "items": {"type": "number"}, "description": "Bar values in the SAME order as categories."},
            "value_prefix": {"type": "string", "description": "Prefix for value labels, default 'Rs '."},
        },
        "required": ["title", "categories", "values"],
    },
}

CHART_LINE_SCHEMA = {
    "name": "chart_line",
    "description": "Render a line chart PNG and return a 'MEDIA:<path>' string. Put that exact string in your reply on its own line and the platform sends it as an image. Use for trends over time like monthly sales. x_labels and values must be the same length and same order.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Chart title."},
            "subtitle": {"type": "string", "description": "Optional one-line subtitle."},
            "x_labels": {"type": "array", "items": {"type": "string"}, "description": "X-axis labels, e.g. ['Feb','Mar','Apr','May','Jun','Jul']."},
            "values": {"type": "array", "items": {"type": "number"}, "description": "Y values in the SAME order as x_labels."},
            "value_prefix": {"type": "string", "description": "Prefix for axis labels, default 'Rs '."},
        },
        "required": ["title", "x_labels", "values"],
    },
}

_TOOLS = [
    ("chart_bar", CHART_BAR_SCHEMA, handle_chart_bar, "📊"),
    ("chart_line", CHART_LINE_SCHEMA, handle_chart_line, "📈"),
]


def register(ctx) -> None:
    """Register the chart tools. Called once by the plugin loader when enabled."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(name=name, toolset="charts", schema=schema, handler=handler, emoji=emoji)
    logger.info("charts plugin: registered %d tools (toolset=charts)", len(_TOOLS))
