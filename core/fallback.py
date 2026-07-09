"""
core/fallback.py
A single reusable "try tool 1 -> tool 2 -> tool 3" executor.
Every module (research, scripting, audio, visuals) plugs its provider
functions into this instead of writing its own try/except chain.
"""

import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fallback")


class AllProvidersFailedError(Exception):
    """Raised when every tool in the fallback chain has failed."""
    pass


def run_with_fallback(providers: list, *args, retries_per_provider: int = 2,
                       retry_delay_sec: int = 5, **kwargs):
    """
    providers: ordered list of (name, callable) tuples, e.g.
        [("gemini", gemini_generate), ("groq", groq_generate), ("cohere", cohere_generate)]
    Each callable is invoked as callable(*args, **kwargs) and must raise
    an exception on failure (rate limit, quota, network error, etc).

    Returns: (result, provider_name_used)
    Raises: AllProvidersFailedError if every provider in the chain fails.
    """
    last_errors = {}

    for name, func in providers:
        for attempt in range(1, retries_per_provider + 1):
            try:
                logger.info(f"Trying provider '{name}' (attempt {attempt}/{retries_per_provider})")
                result = func(*args, **kwargs)
                logger.info(f"Provider '{name}' succeeded.")
                return result, name
            except Exception as e:
                logger.warning(f"Provider '{name}' failed on attempt {attempt}: {e}")
                last_errors[name] = str(e)
                if attempt < retries_per_provider:
                    time.sleep(retry_delay_sec)
        # move to next provider after exhausting retries for this one

    raise AllProvidersFailedError(
        f"All providers failed. Details: {last_errors}"
    )
