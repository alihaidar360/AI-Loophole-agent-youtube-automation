"""
modules/scripting.py
Stage 2: Script Writing Engine.
Provider chain: Groq gpt-oss-120b -> Mistral Large (flagship, free
Experiment tier) -> Groq llama-3.3-70b-versatile (proven safety net).
No Gemini — its model names/SDK changed multiple times this year, making
it unreliable for unattended automation.

Every script goes through a second "critic" pass that revises it against
a concrete quality checklist before being returned.
"""

import json
import re
import requests
from groq import Groq
from config import Config
from core.fallback import run_with_fallback

LONGFORM_SYSTEM_PROMPT = """You are an independent AI researcher who tests
AI tools yourself before reviewing them, writing for a Western (US/UK)
YouTube audience. Speak in first person, like you genuinely used the
tool. Structure the script into these exact chapters, in this order:
(1) Hook - a specific, non-obvious claim, not generic hype
(2) Origin story - who built it, why, what problem it solves
(3) What it actually does - core features in plain language
(4) Hands-on verdict - broken down by specific use-case: what it's
    genuinely great for, what it's weak at, what surprised you
(5) Real limitations - genuine cons, specific, not vague
(6) Final verdict - a clear, earned recommendation, not wishy-washy

Every claim should be specific (numbers, named comparisons) not vague.
Target spoken length: 10-13 minutes (~1500-2000 words).

If the user message includes "what_has_worked_recently", lean into that
real performance data where honest. If it includes "cross_promotion",
reference that other video naturally, once, near the end.

Return STRICT JSON only, no markdown fences, with keys:
"title", "thumbnail_headline", "verdict_sentiment" (one of: "excited",
"skeptical", "neutral"), "video_mood" (e.g. "Minimalist Corporate Blue" or
"Dark Cyberpunk Neon"), "chapters": [{"heading": str, "narration": str}],
"description", "tags": [str]
"""

SHORTS_SYSTEM_PROMPT = """You are the same independent AI researcher as
above, now writing a 45-60 second Short (~130-160 words) for the same
channel. High-retention, listicle/hook structure. Hook must land in the
first 3 seconds — specific and curiosity-driven, never generic. Include
one genuine limitation, not just hype.

If the user message includes "what_has_worked_recently", lean into
whatever has retained/converted well on this channel's past Shorts. If it
includes "cross_promotion", work it into the "cta" naturally, once.

Return STRICT JSON only, no markdown fences, with keys:
"title", "thumbnail_headline", "verdict_sentiment" (one of: "excited",
"skeptical", "neutral"), "video_mood", "hook", "body", "cta",
"description", "tags": [str]
"""

CRITIC_SYSTEM_PROMPT = """You are a ruthless YouTube script editor. You
will be given a draft script as JSON. Find its 3 biggest weaknesses using
this checklist: (1) Is the hook actually surprising, or generic? (2) Is
every claim specific (numbers, named comparisons) or vague? (3) Does the
verdict feel genuinely earned, or bolted on? (4) Any sentence a bored
viewer would skip?

Return STRICT JSON only: {"issues": [str, str, str], "revised_script": <the
full script object, same schema as input, with those 3 issues fixed —
everything else unchanged>}"""


def _build_user_prompt(research: dict, cross_promo: dict = None,
                        performance_insights: dict = None) -> str:
    payload = {
        "tool_name": research["tool_name"],
        "real_user_questions": research["pain_points"][:15],
    }
    if cross_promo:
        payload["cross_promotion"] = {
            "instruction": (
                "Near the end of the script, naturally reference this other "
                "video on the channel to pull viewers toward it — one "
                "sentence is enough, don't sound like an ad."
            ),
            "other_video_title": cross_promo["title"],
        }
    if performance_insights:
        payload["what_has_worked_recently"] = performance_insights
    return json.dumps(payload)


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


def _groq_call(system_prompt: str, user_prompt: str, model: str) -> dict:
    Config.validate(["GROQ_API_KEY"])
    client = Groq(api_key=Config.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return _extract_json(completion.choices[0].message.content)


def _mistral_call(system_prompt: str, user_prompt: str, model: str) -> dict:
    Config.validate(["MISTRAL_API_KEY"])
    resp = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {Config.MISTRAL_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    resp.raise_for_status()
    return _extract_json(resp.json()["choices"][0]["message"]["content"])


def _longform_groq_gptoss(research, cross_promo=None, performance_insights=None) -> dict:
    return _groq_call(LONGFORM_SYSTEM_PROMPT,
                       _build_user_prompt(research, cross_promo, performance_insights),
                       "gpt-oss-120b")


def _longform_mistral_large(research, cross_promo=None, performance_insights=None) -> dict:
    return _mistral_call(LONGFORM_SYSTEM_PROMPT,
                          _build_user_prompt(research, cross_promo, performance_insights),
                          "mistral-large-latest")


def _longform_groq_llama(research, cross_promo=None, performance_insights=None) -> dict:
    return _groq_call(LONGFORM_SYSTEM_PROMPT,
                       _build_user_prompt(research, cross_promo, performance_insights),
                       "llama-3.3-70b-versatile")


def _shorts_groq_gptoss(research, cross_promo=None, performance_insights=None) -> dict:
    return _groq_call(SHORTS_SYSTEM_PROMPT,
                       _build_user_prompt(research, cross_promo, performance_insights),
                       "gpt-oss-120b")


def _shorts_mistral_large(research, cross_promo=None, performance_insights=None) -> dict:
    return _mistral_call(SHORTS_SYSTEM_PROMPT,
                          _build_user_prompt(research, cross_promo, performance_insights),
                          "mistral-large-latest")


def _shorts_groq_llama(research, cross_promo=None, performance_insights=None) -> dict:
    return _groq_call(SHORTS_SYSTEM_PROMPT,
                       _build_user_prompt(research, cross_promo, performance_insights),
                       "llama-3.3-70b-versatile")


def _critic_pass(script: dict, research: dict) -> dict:
    try:
        prompt = json.dumps({"draft_script": script, "tool_name": research.get("tool_name", "")})
        result = _groq_call(CRITIC_SYSTEM_PROMPT, prompt, "gpt-oss-120b")
        revised = result.get("revised_script")
        if revised and ("chapters" in revised or "hook" in revised):
            revised["_provider_used"] = script.get("_provider_used")
            revised["_video_type"] = script.get("_video_type")
            revised["_critic_issues_fixed"] = result.get("issues", [])
            return revised
    except Exception:
        pass
    return script


def generate_longform_script(research: dict, cross_promo: dict = None,
                              performance_insights: dict = None) -> dict:
    providers = [
        ("groq_gpt-oss-120b", _longform_groq_gptoss),
        ("mistral_large", _longform_mistral_large),
        ("groq_llama3.3_70b", _longform_groq_llama),
    ]
    script, provider_used = run_with_fallback(providers, research, cross_promo, performance_insights)
    script["_provider_used"] = provider_used
    script["_video_type"] = "longform"
    return _critic_pass(script, research)


def generate_shorts_script(research: dict, cross_promo: dict = None,
                            performance_insights: dict = None) -> dict:
    providers = [
        ("groq_gpt-oss-120b", _shorts_groq_gptoss),
        ("mistral_large", _shorts_mistral_large),
        ("groq_llama3.3_70b", _shorts_groq_llama),
    ]
    script, provider_used = run_with_fallback(providers, research, cross_promo, performance_insights)
    script["_provider_used"] = provider_used
    script["_video_type"] = "shorts"
    return _critic_pass(script, research)
