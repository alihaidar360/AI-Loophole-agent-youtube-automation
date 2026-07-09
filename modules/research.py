"""
modules/research.py
Stage 1: Research Engine
Finds trending AI tools + real human pain-points/questions about them
using a 3-tier fallback: Google Trends -> Reddit API -> TubeBuddy-style
keyword scrape (simplified free fallback).
"""

from pytrends.request import TrendReq
import praw
import requests
from config import Config
from core.fallback import run_with_fallback


# ---------- Provider 1: Google Trends ----------
def _trends_provider(tool_name: str) -> dict:
    pytrends = TrendReq(hl="en-US", tz=360)
    pytrends.build_payload([tool_name], timeframe="now 7-d", geo="US")
    related = pytrends.related_queries()
    rising = related.get(tool_name, {}).get("rising")
    top = related.get(tool_name, {}).get("top")

    questions = []
    if rising is not None:
        questions += rising["query"].tolist()[:10]
    if top is not None:
        questions += top["query"].tolist()[:10]

    if not questions:
        raise ValueError("No related queries returned by Google Trends")

    return {"source": "google_trends", "questions": questions}


# ---------- Provider 2: Reddit ----------
def _reddit_provider(tool_name: str) -> dict:
    Config.validate(["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"])
    reddit = praw.Reddit(
        client_id=Config.REDDIT_CLIENT_ID,
        client_secret=Config.REDDIT_CLIENT_SECRET,
        user_agent=Config.REDDIT_USER_AGENT,
    )
    subreddits = ["artificial", "ChatGPT", "OpenAI", "SaaS", "productivity"]
    questions = []
    for sub in subreddits:
        for post in reddit.subreddit(sub).search(tool_name, limit=8, sort="relevance"):
            questions.append(post.title)

    if not questions:
        raise ValueError(f"No Reddit discussion found for {tool_name}")

    return {"source": "reddit", "questions": questions[:20]}


# ---------- Provider 3: Simple autocomplete scrape fallback ----------
def _autocomplete_provider(tool_name: str) -> dict:
    """Free fallback: Google/YouTube autocomplete suggestions as a proxy
    for real search intent when Trends and Reddit both fail."""
    resp = requests.get(
        "https://suggestqueries.google.com/complete/search",
        params={"client": "firefox", "q": tool_name},
        timeout=10,
    )
    resp.raise_for_status()
    suggestions = resp.json()[1]
    if not suggestions:
        raise ValueError("No autocomplete suggestions found")
    return {"source": "autocomplete", "questions": suggestions}


def research_tool(tool_name: str) -> dict:
    """
    Main entry point for Stage 1.
    Returns: {
        "tool_name": str,
        "source": str,          # which provider succeeded
        "pain_points": [str],   # real user questions/confusions
    }
    """
    providers = [
        ("google_trends", _trends_provider),
        ("reddit", _reddit_provider),
        ("autocomplete", _autocomplete_provider),
    ]
    result, provider_used = run_with_fallback(providers, tool_name)
    return {
        "tool_name": tool_name,
        "source": provider_used,
        "pain_points": result["questions"],
    }


def get_seo_keywords(tool_name: str, pain_points: list) -> list:
    """Turns raw pain points into a clean keyword list for title/description/tags."""
    base = [tool_name, f"{tool_name} review", f"is {tool_name} worth it",
            f"{tool_name} pros and cons", f"{tool_name} 2026"]
    # Deduplicate, keep it tight (YouTube tags have a total char limit)
    combined = list(dict.fromkeys(base + pain_points))
    return combined[:15]
