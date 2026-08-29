"""
modules/thumbnail.py
Generates the channel's thumbnail: minimal text, a consistent illustrated
"impact" mark whose expression changes with the video's verdict
(excited/skeptical/neutral), pure Pillow — no ImageMagick.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from config import Config

SENTIMENT_COLORS = {
    "excited": ((0, 229, 255), (0, 255, 194)),   # cyan -> green
    "skeptical": ((255, 59, 59), (255, 140, 30)),  # red -> orange
    "neutral": ((0, 229, 255), (255, 46, 196)),   # cyan -> magenta
}


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def generate_thumbnail(headline: str, verdict_sentiment: str, background_image_path: str,
                        out_path: str) -> str:
    """
    headline: short psychological hook text (e.g. "THIS CHANGES CODING FOREVER")
    verdict_sentiment: 'excited' | 'skeptical' | 'neutral'
    background_image_path: one of the video's own b-roll frames, used as backdrop
    """
    W, H = 1280, 720
    colors = SENTIMENT_COLORS.get(verdict_sentiment, SENTIMENT_COLORS["neutral"])

    try:
        bg = Image.open(background_image_path).convert("RGB").resize((W, H))
    except Exception:
        bg = Image.new("RGB", (W, H), (10, 10, 15))

    img = bg.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, int(H * 0.55), W, H], fill=(0, 0, 0, 165))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    font = _load_font(Config.FONT_BLACK, 60) if os.path.exists(Config.FONT_BLACK) else _load_font(Config.FONT_BOLD, 60)

    words = headline.split()
    mid = len(words) // 2 + (len(words) % 2)
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:])

    draw.text((60, H - 220), line1, font=font, fill=colors[0])
    if line2:
        draw.text((60, H - 140), line2, font=font, fill="white")

    img.convert("RGB").save(out_path, quality=92)
    return out_path
