"""
modules/captions.py
Stage 5: Caption Rendering Engine
- Whisper (local, free, open-source) extracts word-level timestamps.
- Pillow renders text onto transparent PNGs (NO MoviePy TextClip / ImageMagick).
- Shorts  -> kinetic captions: one word highlighted at a time, center-screen.
- Longform -> standard subtitles: sentence chunks, bottom-third, semi-transparent box.
"""

import os
import whisper
from PIL import Image, ImageDraw, ImageFont
from config import Config

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        # "base" model balances speed vs accuracy well for a free CI runner.
        _whisper_model = whisper.load_model("base")
    return _whisper_model


def transcribe_with_timestamps(audio_path: str) -> list:
    """Returns a list of word-level dicts: [{"word": str, "start": float, "end": float}]"""
    model = _get_whisper_model()
    result = model.transcribe(audio_path, word_timestamps=True)
    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})
    return words


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    font_path = Config.FONT_BOLD if bold else Config.FONT_REGULAR
    return ImageFont.truetype(font_path, size)


# ---------- Shorts: Kinetic captions ----------
def render_kinetic_caption_frame(all_words: list, active_index: int,
                                  canvas_size: tuple, accent_hex: str,
                                  out_path: str, window: int = 3) -> str:
    """
    Renders ONE PNG frame showing a small window of words around the
    active word, with the active word highlighted and others dimmed.
    Call this once per word; MoviePy stitches the frames on the timeline.
    """
    W, H = canvas_size
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_active = _load_font(size=90, bold=True)
    font_dim = _load_font(size=70, bold=True)

    start = max(0, active_index - window // 2)
    end = min(len(all_words), start + window)
    visible_words = all_words[start:end]

    # Measure total width to center the line
    spacing = 24
    widths = []
    for i, w in enumerate(visible_words):
        font = font_active if (start + i) == active_index else font_dim
        bbox = draw.textbbox((0, 0), w["word"], font=font)
        widths.append(bbox[2] - bbox[0])
    total_width = sum(widths) + spacing * (len(visible_words) - 1)

    x = (W - total_width) / 2
    y_center = H / 2

    for i, w in enumerate(visible_words):
        is_active = (start + i) == active_index
        font = font_active if is_active else font_dim
        fill = accent_hex if is_active else (255, 255, 255, 160)
        bbox = draw.textbbox((0, 0), w["word"], font=font)
        w_height = bbox[3] - bbox[1]
        # Simple black outline for readability over any background
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y_center - w_height / 2 + dy), w["word"], font=font, fill=(0, 0, 0, 200))
        draw.text((x, y_center - w_height / 2), w["word"], font=font, fill=fill)
        x += widths[i] + spacing

    img.save(out_path)
    return out_path


def build_kinetic_caption_clips(words: list, canvas_size: tuple, accent_hex: str,
                                 frames_dir: str):
    """
    Returns a list of (image_path, start_time, duration) tuples ready
    to be turned into MoviePy ImageClips by the assembly module.
    """
    os.makedirs(frames_dir, exist_ok=True)
    clips_meta = []
    for i, w in enumerate(words):
        frame_path = os.path.join(frames_dir, f"word_{i:04d}.png")
        render_kinetic_caption_frame(words, i, canvas_size, accent_hex, frame_path)
        duration = max(w["end"] - w["start"], 0.15)  # floor so very short words are still visible
        clips_meta.append((frame_path, w["start"], duration))
    return clips_meta


# ---------- Long-form: Standard subtitles ----------
def _group_words_into_sentences(words: list, max_chars: int = 70) -> list:
    """Groups word-level timestamps into readable subtitle chunks."""
    chunks = []
    current = []
    current_len = 0
    for w in words:
        current.append(w)
        current_len += len(w["word"]) + 1
        if current_len >= max_chars or w["word"].endswith((".", "!", "?")):
            chunks.append(current)
            current = []
            current_len = 0
    if current:
        chunks.append(current)
    return chunks


def render_subtitle_frame(text: str, canvas_size: tuple, out_path: str) -> str:
    W, H = canvas_size
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(size=48, bold=False)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    box_padding = 24
    box_x0 = (W - text_w) / 2 - box_padding
    box_y0 = H * 0.82
    box_x1 = (W + text_w) / 2 + box_padding
    box_y1 = box_y0 + text_h + box_padding * 2

    draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=12, fill=(0, 0, 0, 140))
    draw.text(((W - text_w) / 2, box_y0 + box_padding / 2), text, font=font, fill=(255, 255, 255, 255))

    img.save(out_path)
    return out_path


def build_subtitle_clips(words: list, canvas_size: tuple, frames_dir: str):
    os.makedirs(frames_dir, exist_ok=True)
    chunks = _group_words_into_sentences(words)
    clips_meta = []
    for i, chunk in enumerate(chunks):
        text = " ".join(w["word"] for w in chunk)
        start = chunk[0]["start"]
        end = chunk[-1]["end"]
        frame_path = os.path.join(frames_dir, f"sub_{i:04d}.png")
        render_subtitle_frame(text, canvas_size, frame_path)
        clips_meta.append((frame_path, start, end - start))
    return clips_meta


def generate_captions(audio_path: str, video_type: str, accent_hex: str, work_dir: str):
    """
    Main entry point for Stage 5.
    video_type: 'shorts' or 'longform'
    """
    words = transcribe_with_timestamps(audio_path)
    canvas_size = Config.SHORTS_SIZE if video_type == "shorts" else Config.LONGFORM_SIZE
    frames_dir = os.path.join(work_dir, "caption_frames")

    if video_type == "shorts":
        return build_kinetic_caption_clips(words, canvas_size, accent_hex, frames_dir)
    else:
        return build_subtitle_clips(words, canvas_size, frames_dir)
