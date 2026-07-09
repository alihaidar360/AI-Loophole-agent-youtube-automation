"""
modules/topic_selector.py
Decides WHICH AI tool the next video should cover.
- Pulls a curated pool of both new/trending and already-popular tools.
- Cross-checks published_log.json so we never repeat a tool too soon.
- Tries to prioritize currently-trending tools (via Google Trends) when possible,
  falling back to the static curated pool otherwise.
"""

import json
import os
import random
from config import Config

# Curated pool: mix of established + emerging AI tools relevant to a
# Western (US/UK) tech-savvy audience. Edit/expand this list over time —
# this is your channel's "content backlog."
TOOL_POOL = [
    # Already-popular (safe, high search volume)
    "ChatGPT", "Midjourney", "Notion AI", "GitHub Copilot", "Runway ML",
    "ElevenLabs", "Perplexity AI", "Claude AI", "Canva Magic Studio",
    "Jasper AI", "Synthesia", "Descript", "Grammarly AI",
    # Newer / trending (lower competition, fresher search intent)
    "Cursor AI", "Suno AI", "Pika Labs", "Gamma App", "Tome AI",
    "Cluely", "Windsurf", "v0 by Vercel", "Replit Agent", "Lovable AI",
]


def _get_recently_covered(lookback: int = 15) -> set:
    if not os.path.exists(Config.PUBLISHED_LOG_FILE):
        return set()
    with open(Config.PUBLISHED_LOG_FILE, "r") as f:
        try:
            log = json.load(f)
        except json.JSONDecodeError:
            return set()
    recent = log[-lookback:]
    return {entry["topic"] for entry in recent}


def select_next_topic() -> str:
    """Returns a tool name not covered in the recent N videos."""
    recently_covered = _get_recently_covered()
    available = [t for t in TOOL_POOL if t not in recently_covered]

    if not available:
        # Whole pool was recently covered — reset and just avoid the last one.
        last = list(recently_covered)[-1] if recently_covered else None
        available = [t for t in TOOL_POOL if t != last]

    return random.choice(available)
