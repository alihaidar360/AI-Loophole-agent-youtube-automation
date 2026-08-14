"""
modules/visuals.py
Stage 4: Visual Assets Engine
- B-roll/images: Pexels -> Pixabay -> Pollinations.ai (AI-generated, always available)
- Background music: automated via modules/sound_library.py (Freesound
  API, CC0-filtered) instead of requiring manually-downloaded files.
  Falls back to a local /assets/music/ file only if the API is
  unavailable — nothing breaks if that folder is empty.

video_mood (e.g. "Dark Cyberpunk Neon", "Minimalist Corporate Blue") is
used to adapt both the search keywords and a hex color palette.

Two entry points for fetching b-roll:
- fetch_visuals(): mood+keyword based, used for a whole video's generic pool
- fetch_visuals_for_query(): ONE specific query per chapter/scene, so each
  segment gets its own relevant footage instead of one generic query
  repeating across the whole video (this is what makes b-roll feel
  "researched" instead of generic-stock-footage).
"""

import os
import requests
from config import Config
from core.fallback import run_with_fallback
from modules import sound_library

MOOD_PROFILES = {
    "Minimalist Corporate Blue": {
        "keywords": ["office", "clean desk", "modern workspace", "blue gradient"],
        "accent_hex": "#2E5AAC",
        "music_query": "corporate ambient",
    },
    "Dark Cyberpunk Neon": {
        "keywords": ["neon city", "futuristic", "cyberpunk", "dark tech"],
        "accent_hex": "#FF2EC4",
        "music_query": "dark tech atmosphere",
    },
    "Apple Minimalist": {
        "keywords": ["white studio", "product shot", "minimal", "clean"],
        "accent_hex": "#1D1D1F",
        "music_query": "minimal ambient calm",
    },
    "default": {
        "keywords": ["technology", "abstract data", "computer screen"],
        "accent_hex": "#00C2A8",
        "music_query": "ambient technology loop",
    },
}


def get_mood_profile(video_mood: str) -> dict:
    return MOOD_PROFILES.get(video_mood, MOOD_PROFILES["default"])


# ---------- Provider 1: Pexels ----------
def _pexels_provider(query: str, count: int, out_dir: str) -> list:
    Config.validate(["PEXELS_API_KEY"])
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": Config.PEXELS_API_KEY},
        params={"query": query, "per_page": count, "orientation": "landscape"},
        timeout=20,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos:
        raise ValueError(f"No Pexels results for '{query}'")

    paths = []
    for i, v in enumerate(videos[:count]):
        link = sorted(v["video_files"], key=lambda f: f.get("width", 0))[-1]["link"]
        out_path = os.path.join(out_dir, f"pexels_{_safe(query)}_{i}.mp4")
        _download(link, out_path)
        paths.append(out_path)
    return paths


# ---------- Provider 2: Pixabay ----------
def _pixabay_provider(query: str, count: int, out_dir: str) -> list:
    Config.validate(["PIXABAY_API_KEY"])
    resp = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": Config.PIXABAY_API_KEY, "q": query, "per_page": count},
        timeout=20,
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    if not hits:
        raise ValueError(f"No Pixabay results for '{query}'")

    paths = []
    for i, hit in enumerate(hits[:count]):
        link = hit["videos"]["medium"]["url"]
        out_path = os.path.join(out_dir, f"pixabay_{_safe(query)}_{i}.mp4")
        _download(link, out_path)
        paths.append(out_path)
    return paths


# ---------- Provider 3: Pollinations.ai (AI-generated images, no API key needed) ----------
def _pollinations_provider(query: str, count: int, out_dir: str) -> list:
    paths = []
    for i in range(count):
        prompt = requests.utils.quote(f"{query}, cinematic, high detail, 16:9")
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=1920&height=1080&nologo=true"
        out_path = os.path.join(out_dir, f"pollinations_{_safe(query)}_{i}.png")
        _download(url, out_path)
        paths.append(out_path)
    if not paths:
        raise ValueError("Pollinations.ai returned no images")
    return paths


def _safe(text: str) -> str:
    """Filesystem-safe short slug for filenames built from a query string."""
    return "".join(c if c.isalnum() else "_" for c in text)[:30]


def _download(url: str, out_path: str):
    r = requests.get(url, timeout=30, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


def _fetch_with_fallback(query: str, count: int, out_dir: str) -> dict:
    """Shared 3-tier fallback logic used by both entry points below."""
    os.makedirs(out_dir, exist_ok=True)
    providers = [
        ("pexels", lambda q, c, d: _pexels_provider(q, c, d)),
        ("pixabay", lambda q, c, d: _pixabay_provider(q, c, d)),
        ("pollinations", lambda q, c, d: _pollinations_provider(q, c, d)),
    ]
    paths, provider_used = run_with_fallback(providers, query, count, out_dir)
    return {"paths": paths, "provider_used": provider_used}


def fetch_visuals(video_mood: str, topic_keywords: list, count: int, out_dir: str) -> dict:
    """Mood+keyword based fetch — used where one broad pool of visuals is
    enough (e.g. Shorts, which are short enough that one relevant query
    covers the whole video)."""
    profile = get_mood_profile(video_mood)
    query = f"{topic_keywords[0]} {profile['keywords'][0]}" if topic_keywords else profile["keywords"][0]
    result = _fetch_with_fallback(query, count, out_dir)
    result["accent_hex"] = profile["accent_hex"]
    return result


def fetch_visuals_for_query(query: str, count: int, out_dir: str) -> dict:
    """ONE specific query — used per chapter/scene in long-form videos so
    each section gets its own relevant footage instead of one generic
    query repeating for the whole video. Does not carry mood/accent info
    (that's fetched once for the whole video via get_mood_profile)."""
    return _fetch_with_fallback(query, count, out_dir)


# ---------- Background music: automated (Freesound) with local fallback ----------
def select_background_music(video_mood: str, out_dir: str) -> dict:
    """
    Returns: {"path": str, "source": "freesound" | "local_fallback" | None}

    Primary: sound_library.fetch_music() — searches Freesound, CC0-only
    (public domain, zero attribution needed), downloads automatically.

    Fallback: if Freesound is unavailable, looks for ANY .mp3 already
    sitting in /assets/music/. If neither is available, returns no music
    rather than failing the whole video.
    """
    profile = get_mood_profile(video_mood)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "background_music.mp3")

    try:
        sound_library.fetch_music(profile["music_query"], out_path)
        return {"path": out_path, "source": "freesound"}
    except Exception:
        pass

    local_dir = Config.MUSIC_DIR
    if os.path.isdir(local_dir):
        local_files = [f for f in os.listdir(local_dir) if f.lower().endswith(".mp3")]
        if local_files:
            return {"path": os.path.join(local_dir, local_files[0]), "source": "local_fallback"}

    return {"path": None, "source": None}
