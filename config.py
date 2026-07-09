"""
config.py
Central configuration loader. ALL secrets come from environment variables,
which in GitHub Actions are injected from GitHub Secrets. Never hardcode keys.
"""

import os


class Config:
    # --- LLM / Scripting APIs ---
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "")

    # --- Research APIs ---
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "yt-automation-bot/1.0")

    # --- Voice APIs ---
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
    GOOGLE_TTS_API_KEY = os.environ.get("GOOGLE_TTS_API_KEY", "")

    # --- Visual APIs ---
    PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
    PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
    # Pollinations.ai needs no key (free, open endpoint)

    # --- YouTube Upload ---
    YT_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID") or os.environ.get("YT_CLIENT_ID", "")
    YT_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET") or os.environ.get("YT_CLIENT_SECRET", "")
    YT_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN") or os.environ.get("YT_REFRESH_TOKEN", "")

    # --- Paths ---
    ASSETS_DIR = "assets"
    STATE_DIR = "pipeline_state"
    FONTS_DIR = "fonts"
    JOB_STATE_FILE = os.path.join(STATE_DIR, "job_state.json")
    PUBLISHED_LOG_FILE = os.path.join(STATE_DIR, "published_log.json")

    # --- Video specs ---
    SHORTS_SIZE = (1080, 1920)
    LONGFORM_SIZE = (1920, 1080)

    # --- Fonts (place free Google Fonts .ttf files in /fonts) ---
    FONT_BOLD = os.path.join(FONTS_DIR, "Montserrat-Bold.ttf")
    FONT_REGULAR = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")

    @classmethod
    def validate(cls, required_keys: list):
        """Call at the start of a module to fail fast with a clear error
        instead of a cryptic exception deep in the pipeline."""
        missing = [k for k in required_keys if not getattr(cls, k)]
        if missing:
            raise EnvironmentError(
                f"Missing required secrets: {missing}. "
                f"Set them in GitHub repo Settings -> Secrets and variables -> Actions."
            )
