"""
modules/sound_design.py
Adds automatic SFX cues (whoosh/impact/click) at cut points and emphasis
moments. SFX are fetched automatically via modules/sound_library.py
(Freesound API, CC0-filtered) instead of requiring manually-downloaded
files, with a local /assets/sfx/ fallback if the API is unavailable.

Shorts get dense cue placement (near every kinetic-caption word beat).
Long-form gets sparse, deliberate placement (chapter transitions via
chapters_with_times, one emphasis hit near the verdict).
"""

import os
from config import Config
from modules import sound_library

CUE_QUERIES = {
    "whoosh": "whoosh transition swipe",
    "impact": "impact hit deep",
    "click": "ui click short",
    "riser": "riser build up short",
}


def _get_sfx(cue_type: str, cache_dir: str) -> str:
    """Fetches (and caches) one SFX file per cue_type. Shared cache dir
    across all jobs — a cue TYPE only ever needs downloading once, not
    once per video."""
    os.makedirs(cache_dir, exist_ok=True)
    out_path = os.path.join(cache_dir, f"{cue_type}.mp3")
    if os.path.exists(out_path):
        return out_path

    query = CUE_QUERIES.get(cue_type, cue_type)
    try:
        sound_library.fetch_sfx(query, out_path)
        return out_path
    except Exception:
        pass

    local_dir = Config.SFX_DIR
    if os.path.isdir(local_dir):
        for fname in os.listdir(local_dir):
            if cue_type in fname.lower() and fname.lower().endswith((".mp3", ".wav")):
                return os.path.join(local_dir, fname)

    return None  # no SFX available for this cue type — skip it, don't fail the video


def generate_sound_cues(video_type: str, total_duration: float, caption_data: dict,
                         chapters_with_times: list = None) -> list:
    """
    video_type: 'shorts' or 'longform'
    total_duration: video length in seconds
    caption_data: {"words": [{"word","start","end"}, ...], "chunks": [...]}
                  — as produced by modules/captions.py
    chapters_with_times: optional, long-form only —
                  [{"heading": str, "start": float}, ...]

    Returns a list of {"sfx_path": str, "start_time": float} cues, ready
    to be passed into the Remotion props as extra Audio sequences.
    """
    cache_dir = os.path.join(Config.ASSETS_DIR, "sfx_cache")
    words = caption_data.get("words", [])
    cues = []

    if video_type == "shorts":
        whoosh_path = _get_sfx("whoosh", cache_dir)
        if whoosh_path:
            cues.append({"sfx_path": whoosh_path, "start_time": 0.0})

        click_path = _get_sfx("click", cache_dir)
        if click_path:
            for i, w in enumerate(words):
                if i % 3 == 0:  # dense but not overwhelming
                    cues.append({"sfx_path": click_path, "start_time": w["start"]})

    else:  # longform
        whoosh_path = _get_sfx("whoosh", cache_dir)
        impact_path = _get_sfx("impact", cache_dir)

        if chapters_with_times and whoosh_path:
            for ch in chapters_with_times:
                cues.append({"sfx_path": whoosh_path, "start_time": ch["start"]})

        if impact_path and total_duration:
            cues.append({"sfx_path": impact_path, "start_time": total_duration * 0.85})

    return cues
