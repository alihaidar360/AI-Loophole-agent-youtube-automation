"""
modules/sound_design.py
Stage: Sound Design Engine (NEW)
Places SFX cues (whoosh on cuts, impact on emphasis, riser on chapter
transitions) onto the timeline. This is what turns "silent cuts" into
something that sounds like a professionally edited video.

Shorts and Long-form get DIFFERENT densities and cue types, matching their
distinct pacing (see Config.FORMATS[video_type]["sfx_density"]):
  - Shorts:   dense — a cue on nearly every cut, matching fast pacing
  - Longform: sparser — cues mainly at chapter transitions and key beats,
              so they punctuate rather than fatigue a 10-13 min video
"""

import os
from config import Config

# Curated free/CC0 SFX set the user downloads once (see README) — same
# pattern as the background-music library: only pre-verified, license-safe
# files are referenced here.
SFX_LIBRARY = {
    "whoosh": os.path.join(Config.SFX_DIR, "whoosh_1.mp3"),
    "impact": os.path.join(Config.SFX_DIR, "impact_1.mp3"),
    "riser": os.path.join(Config.SFX_DIR, "riser_1.mp3"),
    "click": os.path.join(Config.SFX_DIR, "click_1.mp3"),
    "pop": os.path.join(Config.SFX_DIR, "pop_1.mp3"),
}


def _cues_for_shorts(caption_words: list, total_duration: float) -> list:
    """Dense cue placement: a soft 'whoosh' roughly every cut interval,
    plus a 'pop' under the very first word (the hook) for extra punch."""
    fmt = Config.FORMATS["shorts"]
    cut_interval = sum(fmt["cut_pace_sec"]) / 2  # midpoint of the pace range
    cues = []

    if caption_words:
        cues.append({"sfx": SFX_LIBRARY["pop"], "time": 0.0, "volume": 0.7})

    t = cut_interval
    while t < total_duration - 0.5:
        cues.append({"sfx": SFX_LIBRARY["whoosh"], "time": round(t, 2), "volume": 0.35})
        t += cut_interval

    # Emphasize any ALL-CAPS-worthy or exclamation words with an impact cue
    for w in caption_words:
        if w["word"].strip(".,!?").isupper() and len(w["word"]) > 2:
            cues.append({"sfx": SFX_LIBRARY["impact"], "time": w["start"], "volume": 0.5})

    return sorted(cues, key=lambda c: c["time"])


def _cues_for_longform(chapters_with_times: list) -> list:
    """Sparser cue placement: a 'riser' leading into each new chapter, and
    a soft 'click' at chapter start — enough to punctuate structure without
    becoming noisy over 10-13 minutes."""
    cues = []
    for i, chapter in enumerate(chapters_with_times):
        start = chapter["start"]
        if i > 0:
            cues.append({"sfx": SFX_LIBRARY["riser"], "time": max(0, start - 1.0), "volume": 0.3})
        cues.append({"sfx": SFX_LIBRARY["click"], "time": start, "volume": 0.4})
    return sorted(cues, key=lambda c: c["time"])


def generate_sound_cues(video_type: str, total_duration: float,
                         caption_data: dict, chapters_with_times: list = None) -> list:
    """
    Main entry point.
    - video_type: 'shorts' or 'longform'
    - caption_data: output of captions.generate_caption_data()
    - chapters_with_times: for longform only — [{heading, start, end}, ...]
    Returns a flat list of {"sfx": path, "time": float, "volume": float}
    ready to hand to the Remotion assembly step as <Audio> sequences.
    """
    if video_type == "shorts":
        return _cues_for_shorts(caption_data.get("words", []), total_duration)
    else:
        return _cues_for_longform(chapters_with_times or [])
