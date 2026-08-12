"""
modules/scripting.py
Stage 2: Script Writing Engine — "AI Researcher" persona.

Both Shorts and Long-form get a dedicated, fully-specified system prompt —
neither is a cut-down version of the other. Each targets a distinct
pacing, depth, and psychological hook style suited to its format.

Long-form: Gemini 2.5 Pro (primary) -> Groq (fallback)
Shorts:    Groq (primary, fast)     -> Gemini 2.5 Flash (fallback)

Both return: title, thumbnail_headline (news-style psychological hook,
short), verdict_sentiment (excited/skeptical/neutral — drives thumbnail
character expression), video_mood, description, tags.
"""

import json
import google.generativeai as genai
from groq import Groq
from config import Config
from core.fallback import run_with_fallback

# ---------------------------------------------------------------------
# LONG-FORM: 10-13 minute deep-dive, researcher persona, human voice
# ---------------------------------------------------------------------
LONGFORM_SYSTEM_PROMPT = """You are an independent AI researcher who tests
tools hands-on before forming an opinion — think of the tone of a trusted
technical reviewer explaining a finding to a smart friend, not a marketing
narrator and not a dry Wikipedia summary. Write in first person ("I spent a
week with this", "the first thing I noticed was..."). Be specific and
concrete: use real numbers, comparisons, and details rather than vague
adjectives like "powerful" or "amazing".

Structure the script into exactly these chapters, in this order:
1. HOOK (20-30 sec spoken) — open with a specific, curiosity-driving claim
   or question. Do not summarize the whole video here.
2. ORIGIN STORY (60-90 sec) — who built this tool, when, and what specific
   problem they were trying to solve. Use the real details you're given.
3. WHAT IT ACTUALLY DOES (2-3 min) — explain the core mechanism in plain
   language, referencing the REAL user questions/confusions provided to
   you. Do not just list marketing features.
4. HANDS-ON VERDICT (4-5 min, the core of the video) — narrate as if you
   personally used it. For at least 3 distinct use-cases, give a clear,
   specific verdict: what it's genuinely great for, what it's weak at,
   and one surprising finding. This section must feel like earned opinion,
   not a spec sheet.
5. REAL LIMITATIONS (1-2 min) — genuine, specific downsides. This is what
   builds trust — never skip or soften this section.
6. FINAL VERDICT + CTA (45-60 sec) — a direct, opinionated recommendation:
   who should use this and who shouldn't. End with a natural subscribe hook.

Target length: 1550-1950 words total (10-13 minutes spoken).

Also return:
- "thumbnail_headline": a SHORT (3-6 words), ALL CAPS, psychologically
  compelling headline in the indirect style of major news outlets —
  curiosity, stakes, or surprise, NOT the tool's name (e.g. "THIS CHANGES
  EVERYTHING", "DEVELOPERS ARE WORRIED", "NOBODY SAW THIS COMING"). Do not
  put the tool's name in this field.
- "verdict_sentiment": one of "excited", "skeptical", "neutral" — reflecting
  your genuine overall verdict on the tool, used to drive the thumbnail
  character's expression.

If the user message includes a "what_has_worked_recently" field, treat it as
real performance data from this channel's past videos — lean into whatever
hook style, sentiment, or topic pattern it says has performed well, unless
doing so would be dishonest about this specific tool. If it includes a
"cross_promotion" field, follow its instruction exactly once, naturally.

Return STRICT JSON only, no markdown fences, with keys:
"title", "thumbnail_headline", "verdict_sentiment", "video_mood"
(e.g. "Minimalist Corporate Blue" or "Dark Cyberpunk Neon"),
"chapters": [{"heading": str, "narration": str}], "description", "tags": [str]
"""

# ---------------------------------------------------------------------
# SHORTS: 45-60 second high-retention listicle, SAME researcher persona,
# compressed into a single sharp insight rather than a shrunk long-form.
# ---------------------------------------------------------------------
SHORTS_SYSTEM_PROMPT = """You are the same independent AI researcher as
above, but here you have 45-60 seconds, so the entire script is ONE sharp,
specific insight — not a compressed summary of everything. Open with a
hook that lands in the first 3 seconds (a claim, a number, or a question
that creates a genuine curiosity gap). Speak in first person, like you're
telling a friend the one thing about this tool that surprised you. Include
exactly one honest limitation — never pure hype. Close with a single,
punchy line that invites a reaction (comment/follow), not a generic
"like and subscribe".

Target length: 130-165 words total (45-60 seconds spoken).

Also return:
- "thumbnail_headline": SHORT (3-6 words), ALL CAPS, indirect psychological
  hook in the style of major news outlets — NOT the tool's name.
- "verdict_sentiment": one of "excited", "skeptical", "neutral".

If the user message includes a "what_has_worked_recently" field, treat it as
real performance data from this channel's past Shorts and lean into whatever
has been retaining/converting well. If it includes a "cross_promotion"
field, work its instruction into the "cta" naturally, once.

Return STRICT JSON only, no markdown fences, with keys:
"title", "thumbnail_headline", "verdict_sentiment", "video_mood", "hook",
"body", "cta", "description", "tags": [str]
"""


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
                "video on the channel to pull viewers toward it — do not "
                "sound like an ad, one sentence is enough."
            ),
            "other_video_title": cross_promo["title"],
        }

    if performance_insights:
        payload["what_has_worked_recently"] = performance_insights

    return json.dumps(payload)


def _extract_json(text: str) -> dict:
    """Defensive parse — strips markdown fences if a model adds them
    despite instructions."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned)


# ---------- Long-form providers ----------
def _gemini_longform(research: dict, cross_promo=None, performance_insights=None) -> dict:
    Config.validate(["GEMINI_API_KEY"])
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        "gemini-2.5-pro",
        system_instruction=LONGFORM_SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"},
    )
    response = model.generate_content(_build_user_prompt(research, cross_promo, performance_insights))
    return _extract_json(response.text)


def _groq_longform(research: dict, cross_promo=None, performance_insights=None) -> dict:
    Config.validate(["GROQ_API_KEY"])
    client = Groq(api_key=Config.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": LONGFORM_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(research, cross_promo, performance_insights)},
        ],
        response_format={"type": "json_object"},
    )
    return _extract_json(completion.choices[0].message.content)


# ---------- Shorts providers ----------
def _groq_shorts(research: dict, cross_promo=None, performance_insights=None) -> dict:
    Config.validate(["GROQ_API_KEY"])
    client = Groq(api_key=Config.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SHORTS_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(research, cross_promo, performance_insights)},
        ],
        response_format={"type": "json_object"},
    )
    return _extract_json(completion.choices[0].message.content)


def _gemini_shorts(research: dict, cross_promo=None, performance_insights=None) -> dict:
    Config.validate(["GEMINI_API_KEY"])
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=SHORTS_SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"},
    )
    response = model.generate_content(_build_user_prompt(research, cross_promo, performance_insights))
    return _extract_json(response.text)


def generate_longform_script(research: dict, cross_promo: dict = None,
                              performance_insights: dict = None) -> dict:
    providers = [
        ("gemini_2.5_pro", _gemini_longform),
        ("groq_llama3.3_70b", _groq_longform),
    ]
    script, provider_used = run_with_fallback(providers, research, cross_promo, performance_insights)
    script["_provider_used"] = provider_used
    script["_video_type"] = "longform"
    script = _critic_pass(script, research)
    return script


def generate_shorts_script(research: dict, cross_promo: dict = None,
                            performance_insights: dict = None) -> dict:
    providers = [
        ("groq_llama3.3_70b", _groq_shorts),
        ("gemini_2.5_flash", _gemini_shorts),
    ]
    script, provider_used = run_with_fallback(providers, research, cross_promo, performance_insights)
    script["_provider_used"] = provider_used
    script["_video_type"] = "shorts"
    script = _critic_pass(script, research)
    return script


# ---------- Feature: Multi-pass critic (draft -> self-critique -> revise) ----------
CRITIC_SYSTEM_PROMPT = """You are a ruthless YouTube script editor. You will
be given a draft script as JSON. Find its 3 biggest weaknesses using this
checklist: (1) Is the hook actually surprising, or generic? (2) Is every
claim specific (numbers, named comparisons) or vague ("really good",
"very fast")? (3) Does the verdict/opinion feel genuinely earned, or
bolted on? (4) Any sentence a bored viewer would skip?

Return STRICT JSON only: {"issues": [str, str, str], "revised_script": <the
full script object, same schema as the input, with those 3 issues fixed —
everything else unchanged>}"""


def _critic_pass(script: dict, research: dict) -> dict:
    """Runs a second LLM pass that critiques the draft against a concrete
    checklist and returns a revised version. This is what makes the
    output feel closer to 'reasoned about' rather than one-shot generated.
    Never blocks the pipeline — if the critic call fails, the original
    (already good) draft is used unchanged."""
    try:
        prompt = json.dumps({"draft_script": script, "tool_name": research.get("tool_name", "")})
        Config.validate(["GROQ_API_KEY"])
        client = Groq(api_key=Config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        result = _extract_json(completion.choices[0].message.content)
        revised = result.get("revised_script")
        if revised and "chapters" in revised or (revised and "hook" in revised):
            revised["_provider_used"] = script.get("_provider_used")
            revised["_video_type"] = script.get("_video_type")
            revised["_critic_issues_fixed"] = result.get("issues", [])
            return revised
    except Exception:
        pass  # critic pass is a quality boost, never a hard requirement
    return script
