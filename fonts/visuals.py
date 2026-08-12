"""
modules/visuals.py
Stage 4: Visual Assets Engine
B-roll: Pexels -> Pixabay -> Pollinations.ai
Background music: license-verified only, mood-matched.
Both Shorts and Long-form pull from this same engine; the *quantity* and
*query specificity* differ per format (handled by the caller passing
per-sentence-chunk queries rather than one generic query — see
pipeline_runner.py).
"""

import os
import requests
from config import Config
from core.fallback import run_with_fallback

MOOD_PROFILES = {
    "Minimalist Corporate Blue": {
        "keywords": ["office", "clean desk", "modern workspace", "blue gradient"],
        "accent_hex": "#2E5AAC",
    },
    "Dark Cyberpunk Neon": {
        "keywords": ["neon city", "futuristic", "cyberpunk", "dark tech"],
        "accent_hex": "#FF2EC4",
    },
    "Apple Minimalist": {
        "keywords": ["white studio", "product shot", "minimal", "clean"],
        "accent_hex": "#1D1D1F",
    },
    "default": {
        "keywords": ["technology", "abstract data", "computer screen"],
        "accent_hex": "#00C2A8",
    },
}


def get_mood_profile(video_mood: str) -> dict:
    return MOOD_PROFILES.get(video_mood, MOOD_PROFILES["default"])


def _download(url: str, out_path: str):
    r = requests.get(url, timeout=30, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


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
        out_path = os.path.join(out_dir, f"pexels_{query[:20].replace(' ','_')}_{i}.mp4")
        _download(link, out_path)
        paths.append(out_path)
    return paths


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
        out_path = os.path.join(out_dir, f"pixabay_{query[:20].replace(' ','_')}_{i}.mp4")
        _download(link, out_path)
        paths.append(out_path)
    return paths


def _pollinations_provider(query: str, count: int, out_dir: str) -> list:
    paths = []
    for i in range(count):
        prompt = requests.utils.quote(f"{query}, cinematic, high detail, 16:9")
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=1920&height=1080&nologo=true"
        out_path = os.path.join(out_dir, f"pollinations_{query[:20].replace(' ','_')}_{i}.png")
        _download(url, out_path)
        paths.append(out_path)
    if not paths:
        raise ValueError("Pollinations.ai returned no images")
    return paths


def fetch_visuals_for_query(query: str, count: int, out_dir: str) -> dict:
    """Fetch b-roll for ONE specific query (e.g. one sentence-chunk's
    keyword) — called repeatedly per chunk so every segment of the video
    gets relevant, non-generic footage rather than one query for everything."""
    os.makedirs(out_dir, exist_ok=True)
    providers = [
        ("pexels", lambda q, c, d: _pexels_provider(q, c, d)),
        ("pixabay", lambda q, c, d: _pixabay_provider(q, c, d)),
        ("pollinations", lambda q, c, d: _pollinations_provider(q, c, d)),
    ]
    paths, provider_used = run_with_fallback(providers, query, count, out_dir)
    return {"paths": paths, "provider_used": provider_used}


def fetch_visuals(video_mood: str, topic_keywords: list, count: int, out_dir: str) -> dict:
    """Simple single-query fetch (used as a fallback / for the thumbnail
    background). For full-video b-roll, prefer fetch_visuals_for_query
    called once per sentence-chunk from pipeline_runner.py."""
    profile = get_mood_profile(video_mood)
    query = f"{topic_keywords[0]} {profile['keywords'][0]}" if topic_keywords else profile["keywords"][0]
    result = fetch_visuals_for_query(query, count, out_dir)
    return {**result, "accent_hex": profile["accent_hex"]}


SAFE_MUSIC_LIBRARY = {
    "Minimalist Corporate Blue": [
        {"title": "Corporate Ambient 1", "path": "assets/music/corporate_ambient_1.mp3", "license_verified": True},
    ],
    "Dark Cyberpunk Neon": [
        {"title": "Neon Drive", "path": "assets/music/neon_drive.mp3", "license_verified": True},
    ],
    "default": [
        {"title": "Soft Tech Loop", "path": "assets/music/soft_tech_loop.mp3", "license_verified": True},
    ],
}


def select_background_music(video_mood: str) -> dict:
    candidates = SAFE_MUSIC_LIBRARY.get(video_mood, SAFE_MUSIC_LIBRARY["default"])
    verified = [t for t in candidates if t["license_verified"]]
    if not verified:
        verified = SAFE_MUSIC_LIBRARY["default"]
    return verified[0]
