"""
modules/topic_selector.py
Decides which AI tool the next video covers. Runs a competitive-
intelligence check before committing: looks at what's already on
YouTube for a candidate tool so the channel isn't blindly publishing
into an oversaturated topic when a genuine gap exists elsewhere in the pool.
"""

import random
import google.oauth2.credentials
import googleapiclient.discovery
from config import Config
from core import state_manager as sm

TOOL_POOL = [
    "ChatGPT", "Midjourney", "Notion AI", "GitHub Copilot", "Runway ML",
    "ElevenLabs", "Perplexity AI", "Claude AI", "Canva Magic Studio",
    "Jasper AI", "Synthesia", "Descript", "Grammarly AI",
    "Cursor AI", "Suno AI", "Pika Labs", "Gamma App", "Tome AI",
    "Cluely", "Windsurf", "v0 by Vercel", "Replit Agent", "Lovable AI",
]

SATURATION_VIEW_THRESHOLD = 2_000_000
CANDIDATES_TO_CHECK = 5  # keep YouTube Data API quota usage small


def _get_youtube_client():
    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=Config.YT_REFRESH_TOKEN,
        client_id=Config.YT_CLIENT_ID,
        client_secret=Config.YT_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def _check_competitive_gap(youtube, tool_name: str) -> dict:
    try:
        response = youtube.search().list(
            q=f"{tool_name} review", part="id", type="video", order="viewCount", maxResults=3,
        ).execute()
        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        if not video_ids:
            return {"has_demand": False, "oversaturated": False}

        stats = youtube.videos().list(part="statistics", id=",".join(video_ids)).execute()
        view_counts = [int(v["statistics"].get("viewCount", 0)) for v in stats.get("items", [])]
        top_views = max(view_counts) if view_counts else 0

        return {"has_demand": top_views > 1000, "oversaturated": top_views > SATURATION_VIEW_THRESHOLD}
    except Exception:
        return {"has_demand": True, "oversaturated": False}  # neutral fallback


def select_next_topic(video_type: str) -> str:
    recently_covered = sm.get_recently_covered_topics(video_type)
    available = [t for t in TOOL_POOL if t not in recently_covered]
    if not available:
        last = list(recently_covered)[-1] if recently_covered else None
        available = [t for t in TOOL_POOL if t != last]

    if Config.YT_REFRESH_TOKEN and Config.YT_CLIENT_ID:
        try:
            youtube = _get_youtube_client()
            sample = random.sample(available, min(CANDIDATES_TO_CHECK, len(available)))
            good_gaps = []
            for candidate in sample:
                gap = _check_competitive_gap(youtube, candidate)
                if gap["has_demand"] and not gap["oversaturated"]:
                    good_gaps.append(candidate)
            if good_gaps:
                return random.choice(good_gaps)
        except Exception:
            pass

    return random.choice(available)
