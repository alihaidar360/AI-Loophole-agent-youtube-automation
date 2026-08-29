"""
config.py
Central configuration. ALL secrets come from environment variables
(GitHub Secrets in CI). Never hardcode keys. Never commit real values.
"""

import os


class Config:
    # --- Scripting LLM APIs ---
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

    # --- Research APIs ---
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "yt-automation-bot/1.0")

    # --- Voice (priority: Piper local -> Edge-TTS -> ElevenLabs) ---
    # Piper and Edge-TTS need NO API key, NO account, NO billing ever.
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
    PIPER_VOICE = "en_US-ryan-high"
    EDGE_TTS_VOICE = "en-US-ChristopherNeural"
    ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # "Adam"

    # --- Visual APIs ---
    PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
    PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
    # Pollinations.ai needs no key

    # --- Sound library (music + SFX), CC0-only ---
    FREESOUND_API_KEY = os.environ.get("FREESOUND_API_KEY", "")

    # --- YouTube ---
    YT_CLIENT_ID = os.environ.get("YT_CLIENT_ID", "")
    YT_CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET", "")
    YT_REFRESH_TOKEN = os.environ.get("YT_REFRESH_TOKEN", "")

    # --- Paths (all relative to repo root, which is the CWD the
    # orchestrator scripts are always run from) ---
    ASSETS_DIR = "assets"
    STATE_DIR = "pipeline_state"
    FONTS_DIR = "fonts"
    SFX_DIR = os.path.join(ASSETS_DIR, "sfx")
    MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
    JOB_STATE_FILE = os.path.join(STATE_DIR, "job_state.json")
    PUBLISHED_LOG_FILE = os.path.join(STATE_DIR, "published_log.json")
    PERFORMANCE_INSIGHTS_FILE = os.path.join(STATE_DIR, "performance_insights.json")

    # --- Video specs ---
    SHORTS_SIZE = (1080, 1920)
    LONGFORM_SIZE = (1920, 1080)
    FPS = 30

    # --- Fonts ---
    FONT_BOLD = os.path.join(FONTS_DIR, "Montserrat-Bold.ttf")
    FONT_BLACK = os.path.join(FONTS_DIR, "Montserrat-Black.ttf")
    FONT_REGULAR = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")

    # --- Brand ---
    CHANNEL_NAME = "The AI Loophole"
    CHANNEL_HANDLE = "@AILoophole"

    @classmethod
    def validate(cls, required_keys: list):
        missing = [k for k in required_keys if not getattr(cls, k)]
        if missing:
            raise EnvironmentError(
                f"Missing required secrets: {missing}. "
                f"Set them in GitHub repo Settings -> Secrets and variables -> Actions."
            )
