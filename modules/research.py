"""
modules/research.py
Stage 1: Research Engine.
Finds real user pain-points about an AI tool via a 3-tier fallback
(Google Trends -> Reddit -> autocomplete), then does one agentic
follow-up search round to fill whatever gap the first pass missed.
"""

from pytrends.request import TrendReq
import praw
import requests
from groq import Groq
from config import Config
from core.fallback import run_with_fallback


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


def _autocomplete_provider(tool_name: str) -> dict:
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


def _find_research_gap(tool_name: str, pain_points: list) -> str:
    """Feature: agentic multi-hop research. Asks a fast model what
    follow-up search would fill the biggest gap in what's already found.
    Returns None (skip the second hop) if there's nothing meaningfully
    different to search for."""
    try:
        Config.validate(["GROQ_API_KEY"])
        client = Groq(api_key=Config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[{
                "role": "user",
                "content": (
                    f"Tool: {tool_name}\nQuestions already found: {pain_points[:10]}\n\n"
                    "These cover one angle. What's ONE different, specific search "
                    "query (not already covered above) that would surface a "
                    "genuinely different angle — a limitation, a comparison, or a "
                    "specific use-case not yet represented? Reply with ONLY the "
                    "search query text, nothing else. If existing questions "
                    "already cover the topic well, reply with exactly: NONE"
                ),
            }],
        )
        query = completion.choices[0].message.content.strip().strip('"')
        if query.upper() == "NONE" or len(query) < 3:
            return None
        return query
    except Exception:
        return None


def research_tool(tool_name: str) -> dict:
    """
    Returns: {"tool_name": str, "source": str, "pain_points": [str]}
    """
    providers = [
        ("google_trends", _trends_provider),
        ("reddit", _reddit_provider),
        ("autocomplete", _autocomplete_provider),
    ]
    result, provider_used = run_with_fallback(providers, tool_name)
    pain_points = result["questions"]

    follow_up_query = _find_research_gap(tool_name, pain_points)
    if follow_up_query:
        try:
            second_result, _ = run_with_fallback(providers, follow_up_query)
            pain_points = list(dict.fromkeys(pain_points + second_result["questions"]))
        except Exception:
            pass

    return {"tool_name": tool_name, "source": provider_used, "pain_points": pain_points}


def get_seo_keywords(tool_name: str, pain_points: list) -> list:
    base = [tool_name, f"{tool_name} review", f"is {tool_name} worth it",
            f"{tool_name} pros and cons", f"{tool_name} 2026"]
    combined = list(dict.fromkeys(base + pain_points))
    return combined[:15]
