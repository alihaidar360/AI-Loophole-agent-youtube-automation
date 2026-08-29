"""
core/fallback.py
A single reusable "try tool 1 -> tool 2 -> tool 3" executor. Every module
plugs its provider functions into this instead of writing its own
try/except chain.
"""

import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fallback")


class AllProvidersFailedError(Exception):
    pass


def run_with_fallback(providers: list, *args, retries_per_provider: int = 2,
                       retry_delay_sec: int = 5, **kwargs):
    """
    providers: ordered list of (name, callable) tuples.
    Each callable is invoked as callable(*args, **kwargs) and must raise
    on failure.

    Returns: (result, provider_name_used)
    Raises: AllProvidersFailedError if every provider fails.
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

    raise AllProvidersFailedError(f"All providers failed. Details: {last_errors}")
