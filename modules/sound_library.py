"""
modules/sound_library.py
Automates SFX/music discovery via the Freesound API, filtered to CC0
license ONLY (public domain, zero attribution required — the safest
possible license for full automation). Replaces manually downloading
files into /assets/sfx and /assets/music; those folders still work as a
final fallback if this API is ever unavailable.

Free account + API key: https://freesound.org/apiv2/apply — no billing.
"""

import os
import requests
from config import Config

SEARCH_URL = "https://freesound.org/apiv2/search/text/"
CC0_FILTER = 'license:"Creative Commons 0"'


def _search(query: str, max_duration: float = None) -> dict:
    Config.validate(["FREESOUND_API_KEY"])
    filters = [CC0_FILTER]
    if max_duration:
        filters.append(f"duration:[0 TO {max_duration}]")

    resp = requests.get(
        SEARCH_URL,
        params={
            "query": query,
            "filter": " ".join(filters),
            "sort": "rating_desc",
            "fields": "id,name,previews,license,duration",
            "page_size": 5,
            "token": Config.FREESOUND_API_KEY,
        },
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise ValueError(f"No CC0 results for query: {query}")
    return results[0]


def fetch_sfx(query: str, out_path: str) -> str:
    result = _search(query, max_duration=3)
    _download(result["previews"]["preview-hq-mp3"], out_path)
    return out_path


def fetch_music(mood_query: str, out_path: str) -> str:
    result = _search(f"{mood_query} loop background", max_duration=None)
    _download(result["previews"]["preview-hq-mp3"], out_path)
    return out_path


def _download(url: str, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    r = requests.get(url, timeout=30, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
