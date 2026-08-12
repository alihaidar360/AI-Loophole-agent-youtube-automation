"""
core/quality_gate.py
Add #3 (Publish-Before Quality Gate): decides whether a finished video is
confident enough to go straight to "public", or should publish as
"unlisted" with a review flag so a weak video never silently damages the
channel's average performance.

This does NOT block the pipeline or require a human in the loop for
every video — it only downgrades visibility for the minority of videos
that were built from weak fallback sources, and logs why.

Also runs an LLM self-critique pass (feature) that scores the ACTUAL
content — not just which provider built it — against a concrete rubric,
catching the case where every API succeeded but the result is still weak.
"""

import json
from groq import Groq
from config import Config

# Tier ranking per provider — lower tier number = higher confidence.
# Mirrors the actual fallback order defined in each module.
RESEARCH_TIER = {
    "google_trends": 1,
    "reddit": 1,
    "autocomplete": 3,   # weakest fallback — just search-suggest scraping
}

SCRIPT_TIER = {
    "gemini_2.5_pro": 1,
    "gemini_2.5_flash": 1,
    "groq_llama3.3_70b": 2,
}

# A job is downgraded to "unlisted" if its combined score crosses this.
# Tune this over time using the analytics feedback loop (module 3).
CONFIDENCE_THRESHOLD = 4

SELF_SCORE_PROMPT = """Score this finished video script from 1-10 on
whether it would genuinely hook and retain a viewer — be harsh, most
scripts are a 5-6. Consider: is the hook specific or generic? Is the
verdict clearly earned? Would you personally keep watching?
Return STRICT JSON only: {"score": <int 1-10>, "reason": "<one sentence>"}"""


def _self_score_content(script: dict) -> dict:
    """LLM self-critique of the actual finished content, independent of
    which provider built it. Never blocks the pipeline — a failed call
    just skips this extra check and relies on the source-tier score alone."""
    try:
        Config.validate(["GROQ_API_KEY"])
        client = Groq(api_key=Config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SELF_SCORE_PROMPT},
                {"role": "user", "content": json.dumps(script)},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(completion.choices[0].message.content)
    except Exception:
        return {"score": None, "reason": "self-score unavailable"}


def evaluate(research_source: str, script_provider: str, script: dict = None) -> dict:
    """
    Returns: {"publish_as": "public" | "unlisted", "score": int, "reason": str}
    """
    r_tier = RESEARCH_TIER.get(research_source, 3)
    s_tier = SCRIPT_TIER.get(script_provider, 3)
    source_score = r_tier + s_tier

    self_score_result = _self_score_content(script) if script else {"score": None}
    content_score = self_score_result.get("score")

    reasons = []
    downgrade = False

    if source_score >= CONFIDENCE_THRESHOLD:
        downgrade = True
        reasons.append(f"low-confidence sources (research={research_source}, script={script_provider})")

    if content_score is not None and content_score <= 5:
        downgrade = True
        reasons.append(f"self-score {content_score}/10 — {self_score_result.get('reason', '')}")

    if downgrade:
        return {
            "publish_as": "unlisted",
            "score": source_score,
            "content_score": content_score,
            "reason": "; ".join(reasons) + " — published unlisted for manual review.",
        }

    return {
        "publish_as": "public",
        "score": source_score,
        "content_score": content_score,
        "reason": "High-confidence sources and content self-score.",
    }
