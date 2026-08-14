"""
modules/sound_design.py
Adds automatic SFX cues (whoosh/impact/click) at cut points and emphasis
moments — the layer that stops a video from feeling flat/generic.

SFX are NOW AUTOMATED via modules/sound_library.py (Freesound API,
CC0-filtered) instead of requiring manually-downloaded files. Falls back
to a local /assets/sfx/ file only if the API is unavailable.

Shorts get denser cue placement (fast pacing, cut on nearly every beat).
Long-form gets sparser, more deliberate placement (chapter transitions,
key-number reveals) so it doesn't feel gimmicky over 10-13 minutes.
"""

import os
from config import Config
from modules import sound_library

# Query terms used to search Freesound for each cue type. Kept generic/
# game-audio-style terms since that's where most well-rated CC0 SFX live.
CUE_QUERIES = {
    "whoosh": "whoosh transition swipe",
    "impact": "impact hit deep",
    "click": "ui click short",
    "riser": "riser build up short",
}


def _get_sfx(cue_type: str, cache_dir: str) -> str:
    """Fetches (and caches within this job's work dir) one SFX file per
    cue_type, so a 60-cue Short only triggers a handful of Freesound
    searches, not 60 — cue TYPE is fetched once, then reused at every
    timestamp that needs that type of sound."""
    out_path = os.path.join(cache_dir, f"{cue_type}.mp3")
    if os.path.exists(out_path):
        return out_path

    query = CUE_QUERIES.get(cue_type, cue_type)
    try:
        sound_library.fetch_sfx(query, out_path)
        return out_path
    except Exception:
        pass  # fall through to local fallback below

    local_dir = Config.SFX_DIR
    if os.path.isdir(local_dir):
        for fname in os.listdir(local_dir):
            if cue_type in fname.lower() and fname.lower().endswith((".mp3", ".wav")):
                return os.path.join(local_dir, fname)

    return None  # no SFX available for this cue type — skip it, don't fail the video


def generate_sound_cues(caption_meta: list, video_type: str, work_dir: str) -> list:
    """
    caption_meta: the word/subtitle timing list produced by modules/captions.py
    video_type: 'shorts' or 'longform'

    Returns a list of {"sfx_path": str, "start_time": float} cues, ready
    to be passed into the Remotion props as extra Audio sequences.
    """
    cache_dir = os.path.join(work_dir, "sfx_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cues = []

    if video_type == "shorts":
        # Dense: a soft click on nearly every kinetic-caption word beat,
        # plus a whoosh at the very start (hook impact).
        whoosh_path = _get_sfx("whoosh", cache_dir)
        if whoosh_path:
            cues.append({"sfx_path": whoosh_path, "start_time": 0.0})

        click_path = _get_sfx("click", cache_dir)
        if click_path:
            # every 3rd word beat — dense but not overwhelming
            for i, item in enumerate(caption_meta):
                start = item[1] if isinstance(item, (list, tuple)) else item.get("start", 0)
                if i % 3 == 0:
                    cues.append({"sfx_path": click_path, "start_time": start})

    else:  # longform
        # Sparse: whoosh only at chapter-style gaps (big time jumps
        # between caption chunks signal a new section), impact only
        # occasionally for emphasis — deliberate, not gimmicky.
        whoosh_path = _get_sfx("whoosh", cache_dir)
        impact_path = _get_sfx("impact", cache_dir)

        prev_end = 0.0
        for i, item in enumerate(caption_meta):
            start = item[1] if isinstance(item, (list, tuple)) else item.get("start", 0)
            gap = start - prev_end
            if gap > 2.5 and whoosh_path:  # a real pause = likely a chapter/topic shift
                cues.append({"sfx_path": whoosh_path, "start_time": start})
            prev_end = start

        # one impact cue near the video's likely "verdict" moment (~85% mark)
        if caption_meta and impact_path:
            total_items = len(caption_meta)
            verdict_item = caption_meta[int(total_items * 0.85)]
            verdict_start = verdict_item[1] if isinstance(verdict_item, (list, tuple)) else verdict_item.get("start", 0)
            cues.append({"sfx_path": impact_path, "start_time": verdict_start})

    return cues
