"""
modules/audio.py
Stage 3: Voiceover Engine
Primary: Edge-TTS (free, unlimited, US neutral voice)
Fallback 1: ElevenLabs free tier
Fallback 2: Google Cloud TTS free tier
"""
from gtts import gTTS
import asyncio
import os
import requests
import edge_tts
from config import Config
from core.fallback import run_with_fallback

US_VOICE = "en-US-GuyNeural"  # neutral American male; swap to en-US-JennyNeural for female


# ---------- Provider 1: Edge-TTS ----------
def _edge_tts_provider(text: str, output_path: str) -> str:
    async def _run():
        communicate = edge_tts.Communicate(text, US_VOICE)
        await communicate.save(output_path)

    asyncio.run(_run())
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Edge-TTS produced an empty file")
    return output_path


# ---------- Provider 2: ElevenLabs ----------
def _elevenlabs_provider(text: str, output_path: str) -> str:
    Config.validate(["ELEVENLABS_API_KEY"])
    voice_id = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" — neutral US voice
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": Config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code == 429:
        raise RuntimeError("ElevenLabs free tier quota exceeded")
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return output_path


# ---------- Provider 3: Google Cloud TTS ----------

def generate_google_tts(text, output_file):
    # Free gTTS - No API Key Needed
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(output_file)
    return output_file

def generate_voiceover(text: str, output_path: str) -> dict:
    """
    Returns: {"path": str, "provider_used": str}
    """
    providers = [
        ("edge_tts", lambda t, p: _edge_tts_provider(t, p)),
        ("elevenlabs", lambda t, p: _elevenlabs_provider(t, p)),
        ("google_tts", lambda t, p: generate_google_tts(t, p)),
    ]
    path, provider_used = run_with_fallback(providers, text, output_path)
    return {"path": path, "provider_used": provider_used}
