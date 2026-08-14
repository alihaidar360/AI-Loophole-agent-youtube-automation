"""
config.py
Central configuration. All secrets from environment (GitHub Secrets).
Both Shorts and Long-form get explicit, independent settings throughout
this file — neither format is treated as an afterthought.
"""

import os


class Config:
    # --- LLM / Scripting APIs ---
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    # --- Research APIs ---
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "yt-automation-bot/1.0")

    # --- Voice (priority order: Piper (local, offline) -> Edge-TTS -> ElevenLabs) ---
    # Piper and Edge-TTS need NO API key, NO account, and NO billing ever —
    # both run/stream for free with zero payment info involved anywhere.
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
    # American, professional-researcher-sounding male voices, per provider:
    PIPER_VOICE = "en_US-ryan-high"               # local neural voice (MIT license, runs on CPU)
    EDGE_TTS_VOICE = "en-US-ChristopherNeural"    # deep, authoritative fallback
    ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # "Adam" — confident American male

    # --- Visual APIs ---
    PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
    PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
    # Pollinations.ai needs no key

    # --- YouTube Upload ---
    YT_CLIENT_ID = os.environ.get("YT_CLIENT_ID", "")
    YT_CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET", "")
    YT_REFRESH_TOKEN = os.environ.get("YT_REFRESH_TOKEN", "")

    # --- Paths ---
    ASSETS_DIR = "assets"
    STATE_DIR = "pipeline_state"
    FONTS_DIR = "fonts"
    SFX_DIR = "assets/sfx"
    MUSIC_DIR = "assets/music"
    REMOTION_DIR = "remotion"
    JOB_STATE_FILE = os.path.join(STATE_DIR, "job_state.json")
    PUBLISHED_LOG_FILE = os.path.join(STATE_DIR, "published_log.json")

    # --- Format specs: Shorts and Long-form each fully specified, independently ---
    FORMATS = {
        "shorts": {
            "size": (1080, 1920),
            "fps": 30,
            "target_duration_sec": (45, 60),
            "target_words": (130, 165),
            "caption_style": "kinetic",       # big, center-screen, one word at a time
            "cut_pace_sec": (1.2, 2.0),       # fast cuts for retention
            "zoom_intensity": "high",         # aggressive Ken Burns
            "sfx_density": "high",            # a sound cue on nearly every cut
            "cover_size": (1080, 1920),
        },
        "longform": {
            "size": (1920, 1080),
            "fps": 30,
            "target_duration_sec": (600, 780),  # 10-13 min
            "target_words": (1550, 1950),
            "caption_style": "subtitle",        # bottom-third standard subtitles
            "cut_pace_sec": (4.0, 7.0),         # slower, documentary-style pacing
            "zoom_intensity": "medium",
            "sfx_density": "medium",            # cues on chapter changes / key beats only
            "cover_size": (1280, 720),
        },
    }

    FONT_BOLD = os.path.join(FONTS_DIR, "Montserrat-Bold.ttf")
    FONT_REGULAR = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")
    FONT_BLACK = os.path.join(FONTS_DIR, "Montserrat-Black.ttf")

    @classmethod
    def validate(cls, required_keys: list):
        missing = [k for k in required_keys if not getattr(cls, k)]
        if missing:
            raise EnvironmentError(
                f"Missing required secrets: {missing}. "
                f"Set them in GitHub repo Settings -> Secrets and variables -> Actions."
            )
