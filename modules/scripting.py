"""
modules/scripting.py
Stage 2: Script Writing Engine
Long-form: Gemini 1.5 Pro (primary) -> Claude -> Groq (Llama 3.3 70B)
Shorts:    Groq (primary, fast)     -> Gemini      -> Cohere

Every script generation also returns a "video_mood" tag so the visuals
module can pick matching colors/keywords.
"""

import json
import google.generativeai as genai
from groq import Groq
from config import Config
from core.fallback import run_with_fallback

LONGFORM_SYSTEM_PROMPT = """You are an expert AI/tech reviewer writing for a Western
(US/UK) YouTube audience. Write a structured, chaptered deep-dive script about the
tool below. Use the real user pain points provided to directly answer what people
are actually confused about. Be balanced: include genuine strengths AND genuine
weaknesses/limitations. No hype, no filler. Target spoken length: 12-15 minutes
(~1800-2200 words). Return STRICT JSON with keys:
"title", "video_mood" (e.g. "Minimalist Corporate Blue" or "Dark Cyberpunk Neon"),
"chapters": [{"heading": str, "narration": str}], "description", "tags": [str]
"""

SHORTS_SYSTEM_PROMPT = """You are a viral Shorts scriptwriter for a Western tech
audience. Write a 45-60 second script (~130-160 words) about the tool below,
structured as a high-retention listicle/hook. Hook must land in the first 3
seconds. Be honest — include one real limitation, not just hype. Return STRICT
JSON with keys: "title", "video_mood", "hook", "body" (str), "cta",
"description", "tags": [str]
"""


def _build_user_prompt(research: dict) -> str:
    return json.dumps({
        "tool_name": research["tool_name"],
        "real_user_questions": research["pain_points"][:15],
    })


# ---------- Long-form providers ----------
def _gemini_longform(research: dict) -> dict:
    Config.validate(["GEMINI_API_KEY"])
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        "gemini-1.5-pro",
        system_instruction=LONGFORM_SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"},
    )
    response = model.generate_content(_build_user_prompt(research))
    return json.loads(response.text)


def _groq_longform(research: dict) -> dict:
    Config.validate(["GROQ_API_KEY"])
    client = Groq(api_key=Config.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": LONGFORM_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(research)},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(completion.choices[0].message.content)


# ---------- Shorts providers ----------
def _groq_shorts(research: dict) -> dict:
    Config.validate(["GROQ_API_KEY"])
    client = Groq(api_key=Config.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SHORTS_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(research)},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(completion.choices[0].message.content)


def _gemini_shorts(research: dict) -> dict:
    Config.validate(["GEMINI_API_KEY"])
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        "gemini-1.5-flash",  # faster/cheaper model fits shorts better
        system_instruction=SHORTS_SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"},
    )
    response = model.generate_content(_build_user_prompt(research))
    return json.loads(response.text)


def generate_longform_script(research: dict) -> dict:
    providers = [
        ("gemini_1.5_pro", _gemini_longform),
        ("groq_llama3.3_70b", _groq_longform),
    ]
    script, provider_used = run_with_fallback(providers, research)
    script["_provider_used"] = provider_used
    return script


def generate_shorts_script(research: dict) -> dict:
    providers = [
        ("groq_llama3.3_70b", _groq_shorts),
        ("gemini_1.5_flash", _gemini_shorts),
    ]
    script, provider_used = run_with_fallback(providers, research)
    script["_provider_used"] = provider_used
    return script
