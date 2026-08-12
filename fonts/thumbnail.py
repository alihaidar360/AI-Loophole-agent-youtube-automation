"""
modules/thumbnail.py
Stage: Thumbnail / Cover Generator (Pillow-only, no ImageMagick, no
external image-gen API — fully free and CI-safe).

Research-backed design (see conversation): the highest-performing AI-tools
channel on YouTube uses a bright, colorful background with an expressive
CARTOON version of the host reacting to the tool — not a photoreal face,
not a wall of text. This module reproduces that formula:
  - Bright warm gradient background
  - One consistent illustrated character with 3 expression variants
    (excited / skeptical / neutral) driven by the script's verdict_sentiment
  - A short, ALL-CAPS, psychologically-framed headline (from scripting.py's
    "thumbnail_headline" field) — never the raw tool name as the headline
  - A small mock "app UI" card representing the tool being reacted to
  - Tool name kept small, secondary

Both Shorts (1080x1920 cover) and Long-form (1280x720 thumbnail) are
fully supported with their own layouts — not one stretched to fit the other.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from config import Config


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _vertical_gradient(size, top_color, bottom_color) -> Image.Image:
    w, h = size
    top = np.array(top_color, dtype=float)
    bottom = np.array(bottom_color, dtype=float)
    grad = np.linspace(0, 1, h)[:, None] * (bottom - top) + top
    grad = np.tile(grad[:, None, :], (1, w, 1)).astype(np.uint8)
    return Image.fromarray(grad, mode="RGB")


def _draw_character(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, sentiment: str):
    """Draws the consistent illustrated 'researcher' character. Only the
    eyes/eyebrows/mouth change between expressions — silhouette stays
    identical across every video for brand recognition.

    NOTE: brows/mouth use a LIGHT color (not `dark`) because they sit on
    top of the dark head fill — same-color-on-same-color was a bug in an
    earlier draft that made them invisible."""
    s = scale
    head_rx, head_ry = int(230 * s), int(245 * s)
    dark = (26, 20, 40)
    feature_light = (215, 208, 235)   # brows / closed-mouth lines
    mouth_open_color = (222, 92, 100)  # open-mouth "O" — warm, visible on dark

    # hair/head silhouette
    draw.ellipse([cx - head_rx, cy - head_ry, cx + head_rx, cy + head_ry], fill=dark)
    hair_top = cy - head_ry
    draw.pieslice([cx - head_rx - 10, hair_top - 40, cx + head_rx + 10, hair_top + int(180 * s)],
                  180, 360, fill=(20, 15, 32))

    eye_dx, eye_dy = int(75 * s), int(-10 * s)
    eye_rx, eye_ry = int(42 * s), int(50 * s)

    if sentiment == "excited":
        # wide eyes, raised brows, open "whoa" mouth
        for sign in (-1, 1):
            ex = cx + sign * eye_dx
            ey = cy + eye_dy
            draw.ellipse([ex - eye_rx, ey - eye_ry, ex + eye_rx, ey + eye_ry], fill="white")
            draw.ellipse([ex - eye_rx * 0.45, ey - eye_ry * 0.35, ex + eye_rx * 0.45, ey + eye_ry * 0.55],
                         fill=dark)
            draw.arc([ex - 55 * s, ey - 110 * s, ex + 55 * s, ey - 40 * s], 200, 340,
                      fill=feature_light, width=int(9 * s))
        mouth_w, mouth_h = int(50 * s), int(38 * s)
        mouth_cy = cy + int(115 * s)
        draw.ellipse([cx - mouth_w, mouth_cy - mouth_h, cx + mouth_w, mouth_cy + mouth_h],
                     fill=mouth_open_color, outline=feature_light, width=int(4 * s))

    elif sentiment == "skeptical":
        # narrowed eyes, one raised brow, flat/smirk mouth
        for sign in (-1, 1):
            ex = cx + sign * eye_dx
            ey = cy + eye_dy
            draw.ellipse([ex - eye_rx, ey - eye_ry * 0.55, ex + eye_rx, ey + eye_ry * 0.55], fill="white")
            draw.ellipse([ex - eye_rx * 0.4, ey - eye_ry * 0.25, ex + eye_rx * 0.4, ey + eye_ry * 0.25],
                         fill=dark)
        draw.line([cx - eye_dx - 40 * s, cy + eye_dy - 60 * s, cx - eye_dx + 40 * s, cy + eye_dy - 50 * s],
                  fill=feature_light, width=int(9 * s))
        draw.line([cx + eye_dx - 40 * s, cy + eye_dy - 40 * s, cx + eye_dx + 40 * s, cy + eye_dy - 65 * s],
                  fill=feature_light, width=int(9 * s))
        mouth_cy = cy + int(115 * s)
        draw.line([cx - 50 * s, mouth_cy, cx + 60 * s, mouth_cy - 15 * s], fill=feature_light, width=int(14 * s))

    else:  # neutral
        for sign in (-1, 1):
            ex = cx + sign * eye_dx
            ey = cy + eye_dy
            draw.ellipse([ex - eye_rx * 0.85, ey - eye_ry * 0.75, ex + eye_rx * 0.85, ey + eye_ry * 0.75],
                         fill="white")
            draw.ellipse([ex - eye_rx * 0.4, ey - eye_ry * 0.35, ex + eye_rx * 0.4, ey + eye_ry * 0.35],
                         fill=dark)
        mouth_cy = cy + int(105 * s)
        draw.arc([cx - 90 * s, mouth_cy - 40 * s, cx + 90 * s, mouth_cy + 40 * s], 20, 160,
                  fill=feature_light, width=int(12 * s))


def _draw_mock_ui_card(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=24, fill="white")
    draw.rounded_rectangle([x, y, x + w, y + 70], radius=24, fill=(26, 20, 40))
    draw.rectangle([x, y + 46, x + w, y + 70], fill=(26, 20, 40))
    for i, color in enumerate([(255, 94, 58), (255, 184, 0), (74, 222, 128)]):
        draw.ellipse([x + 35 + i * 30, y + 35, x + 53 + i * 30, y + 53], fill=color)
    line_y = y + 100
    for lw in [0.8, 0.65, 0.72]:
        draw.rounded_rectangle([x + 30, line_y, x + 30 + int(w * lw * 0.8), line_y + 20], radius=6,
                                fill=(229, 231, 235))
        line_y += 42
    btn_y = line_y + 15
    draw.rounded_rectangle([x + 30, btn_y, x + 30 + int(w * 0.35), btn_y + 50], radius=10, fill=(255, 94, 58))


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_longform_thumbnail(headline: str, tool_name: str, sentiment: str, out_path: str) -> str:
    W, H = Config.FORMATS["longform"]["cover_size"]
    img = _vertical_gradient((W, H), (255, 184, 0), (255, 94, 58))
    draw = ImageDraw.Draw(img)

    # Character sits lower so the headline band above never overlaps it.
    _draw_character(draw, cx=310, cy=470, scale=0.92, sentiment=sentiment)
    _draw_mock_ui_card(draw, x=620, y=400, w=480, h=280)

    font_headline = _load_font(Config.FONT_BLACK, 54)
    lines = _wrap_text(draw, headline.upper(), font_headline, W - 90)
    if len(lines) > 2:
        # headline too long for 2 lines at this size — shrink once rather
        # than overflow off-canvas
        font_headline = _load_font(Config.FONT_BLACK, 44)
        lines = _wrap_text(draw, headline.upper(), font_headline, W - 90)
    y = 55
    for line in lines[:2]:
        draw.text((W / 2, y), line, font=font_headline, fill=(26, 20, 40), anchor="ma")
        y += 62

    font_tag = _load_font(Config.FONT_BOLD, 30)
    draw.rounded_rectangle([40, H - 80, 40 + draw.textlength(tool_name.upper(), font=font_tag) + 50, H - 30],
                            radius=20, fill=(26, 20, 40))
    draw.text((65, H - 68), tool_name.upper(), font=font_tag, fill="white")

    img.save(out_path, quality=92)
    return out_path


def generate_shorts_cover(headline: str, tool_name: str, sentiment: str, out_path: str) -> str:
    """Shorts cover: portrait layout — character large and centered-top,
    headline mid-frame, tool badge near the bottom. Designed for the
    cover-frame YouTube shows in feeds, not the in-video captions."""
    W, H = Config.FORMATS["shorts"]["cover_size"]
    img = _vertical_gradient((W, H), (255, 184, 0), (255, 94, 58))
    draw = ImageDraw.Draw(img)

    _draw_character(draw, cx=W // 2, cy=520, scale=1.15, sentiment=sentiment)

    font_headline = _load_font(Config.FONT_BLACK, 74)
    lines = _wrap_text(draw, headline.upper(), font_headline, W - 100)
    y = 950
    for line in lines[:3]:
        draw.text((W / 2, y), line, font=font_headline, fill=(26, 20, 40), anchor="ma")
        y += 88

    font_tag = _load_font(Config.FONT_BOLD, 40)
    tag_w = draw.textlength(tool_name.upper(), font=font_tag) + 60
    draw.rounded_rectangle([(W - tag_w) / 2, H - 160, (W + tag_w) / 2, H - 90], radius=24, fill=(26, 20, 40))
    draw.text((W / 2, H - 145), tool_name.upper(), font=font_tag, fill="white", anchor="ma")

    img.save(out_path, quality=92)
    return out_path


def generate_thumbnail(video_type: str, headline: str, tool_name: str, sentiment: str, out_path: str) -> str:
    """Dispatches to the correctly-shaped generator for the format —
    Shorts and Long-form never share a stretched/cropped image."""
    if video_type == "shorts":
        return generate_shorts_cover(headline, tool_name, sentiment, out_path)
    return generate_longform_thumbnail(headline, tool_name, sentiment, out_path)
