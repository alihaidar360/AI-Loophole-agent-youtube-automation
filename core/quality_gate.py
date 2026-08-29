"""
core/quality_gate.py
Decides whether a finished video is confident enough to publish "public",
or should go "unlisted" with a review flag. Combines two signals:
(1) which fallback tier built the research/script, (2) an LLM
self-critique score of the ACTUAL finished content.
"""

import json
from groq import Groq
from config import Config

RESEARCH_TIER = {
    "google_trends": 1,
    "reddit": 1,
    "autocomplete": 3,
}

SCRIPT_TIER = {
    "groq_openai_gpt-oss-120b": 1,
    "mistral_large": 1,
    "groq_openai_gpt-oss-20b": 2,
}

CONFIDENCE_THRESHOLD = 4  # source_score >= this => downgrade to unlisted

SELF_SCORE_PROMPT = """Score this finished video script from 1-10 on
whether it would genuinely hook and retain a viewer — be harsh, most
scripts are a 5-6. Consider: is the hook specific or generic? Is the
verdict clearly earned? Would you personally keep watching?
Return STRICT JSON only: {"score": <int 1-10>, "reason": "<one sentence>"}"""


def _self_score_content(script: dict) -> dict:
    try:
        Config.validate(["GROQ_API_KEY"])
        client = Groq(api_key=Config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
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
