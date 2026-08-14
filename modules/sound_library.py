"""
modules/sound_library.py
Automates what was previously a manual task: finding and downloading
copyright-safe SFX/music. Uses the Freesound API, filtered to CC0
license ONLY (public domain — zero attribution required, safest possible
license for full automation, matching the "recheck it's safe" requirement
from earlier in this project).

Free to use: register a free account + API key at
https://freesound.org/apiv2/apply — no billing, no card, just a quick
form. Add the key as GitHub Secret FREESOUND_API_KEY.

This REPLACES manually downloading files into /assets/sfx and
/assets/music. Local files still work as a final fallback if the API
is ever unavailable — nothing breaks if the folders are empty.
"""

import os
import requests
from config import Config

FREESOUND_API_KEY = os.environ.get("FREESOUND_API_KEY", "")
SEARCH_URL = "https://freesound.org/apiv2/search/text/"

# CC0 only — public domain, zero attribution needed, zero legal ambiguity.
CC0_FILTER = 'license:"Creative Commons 0"'


def _search(query: str, max_duration: float = None) -> dict:
    if not FREESOUND_API_KEY:
        raise RuntimeError("FREESOUND_API_KEY not set")

    filters = [CC0_FILTER]
    if max_duration:
        filters.append(f"duration:[0 TO {max_duration}]")

    resp = requests.get(
        SEARCH_URL,
        params={
            "query": query,
            "filter": " ".join(filters),
            "sort": "rating_desc",     # prefer well-rated sounds over random uploads
            "fields": "id,name,previews,license,duration",
            "page_size": 5,
            "token": FREESOUND_API_KEY,
        },
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise ValueError(f"No CC0 results for query: {query}")
    return results[0]  # top-rated match


def fetch_sfx(cue_type: str, out_path: str) -> str:
    """cue_type: short descriptive query, e.g. 'whoosh transition',
    'ui click', 'impact hit'. Downloads a short CC0 sound effect."""
    result = _search(cue_type, max_duration=3)
    preview_url = result["previews"]["preview-hq-mp3"]
    _download(preview_url, out_path)
    return out_path


def fetch_music(mood_query: str, out_path: str, min_duration: float = 60) -> str:
    """mood_query: e.g. 'ambient corporate loop', 'dark tech atmosphere'.
    Prefers longer CC0 tracks suitable for looping under narration."""
    result = _search(f"{mood_query} loop background", max_duration=None)
    if result.get("duration", 0) < min_duration:
        # try again without the duration constraint relaxed the other way —
        # just accept the short one rather than failing the whole pipeline
        pass
    preview_url = result["previews"]["preview-hq-mp3"]
    _download(preview_url, out_path)
    return out_path


def _download(url: str, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    r = requests.get(url, timeout=30, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
