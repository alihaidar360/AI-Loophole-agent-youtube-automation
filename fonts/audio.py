"""
modules/audio.py
Stage 3: Voiceover Engine
Priority: Piper TTS (local, offline, zero setup) -> Edge-TTS (unlimited,
zero setup) -> ElevenLabs (small free tier, optional premium backup).

Both Piper and Edge-TTS need NO API key, NO account signup, and NO
billing information anywhere — they either run locally on the GitHub
Actions runner (Piper) or stream from a free public endpoint (Edge-TTS).
ElevenLabs is an optional extra, never required for the pipeline to work.

Same provider order and same American-researcher voice used for BOTH
Shorts and Long-form — consistency across formats matters for brand voice.
"""

import asyncio
import os
import subprocess
import requests
import edge_tts
from config import Config
from core.fallback import run_with_fallback

PIPER_MODEL_DIR = os.path.join(Config.ASSETS_DIR, "piper_models")
PIPER_MODEL_URL_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US"


def _ensure_piper_model() -> tuple:
    """Downloads the Piper voice model files once (public, no auth, no
    billing) and caches them under assets/ so GitHub Actions' cache
    action can persist them across runs instead of re-downloading daily."""
    os.makedirs(PIPER_MODEL_DIR, exist_ok=True)
    voice = Config.PIPER_VOICE  # e.g. "en_US-ryan-high"
    name, quality = voice.rsplit("-", 1)
    speaker = name.split("-", 1)[1] if "-" in name else name  # "ryan"

    onnx_path = os.path.join(PIPER_MODEL_DIR, f"{voice}.onnx")
    json_path = os.path.join(PIPER_MODEL_DIR, f"{voice}.onnx.json")

    if not os.path.exists(onnx_path):
        url = f"{PIPER_MODEL_URL_BASE}/{speaker}/{quality}/{voice}.onnx"
        _download(url, onnx_path)
    if not os.path.exists(json_path):
        url = f"{PIPER_MODEL_URL_BASE}/{speaker}/{quality}/{voice}.onnx.json"
        _download(url, json_path)

    return onnx_path, json_path


def _download(url: str, out_path: str):
    r = requests.get(url, timeout=60, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


# ---------- Provider 1: Piper TTS (local, offline) — PRIMARY ----------
def _piper_provider(text: str, output_path: str) -> str:
    onnx_path, _ = _ensure_piper_model()

    wav_path = output_path.rsplit(".", 1)[0] + ".wav"
    result = subprocess.run(
        ["python3", "-m", "piper", "--model", onnx_path, "--output_file", wav_path],
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=300,
    )
    if result.returncode != 0 or not os.path.exists(wav_path):
        raise RuntimeError(f"Piper TTS failed: {result.stderr.decode(errors='ignore')}")

    # Convert to mp3 for consistency with the rest of the pipeline (ffmpeg
    # is already a required system dependency for whisper/remotion).
    subprocess.run(["ffmpeg", "-y", "-i", wav_path, output_path],
                    capture_output=True, timeout=60, check=True)
    os.remove(wav_path)

    if os.path.getsize(output_path) == 0:
        raise RuntimeError("Piper TTS produced an empty file")
    return output_path


# ---------- Provider 2: Edge-TTS (free streaming endpoint) — SECONDARY ----------
def _edge_tts_provider(text: str, output_path: str) -> str:
    async def _run():
        communicate = edge_tts.Communicate(text, Config.EDGE_TTS_VOICE)
        await communicate.save(output_path)

    asyncio.run(_run())
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Edge-TTS produced an empty file")
    return output_path


# ---------- Provider 3: ElevenLabs (optional premium backup) — TERTIARY ----------
def _elevenlabs_provider(text: str, output_path: str) -> str:
    Config.validate(["ELEVENLABS_API_KEY"])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{Config.ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": Config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.55, "similarity_boost": 0.75},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code == 429:
        raise RuntimeError("ElevenLabs free tier quota exceeded")
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return output_path


def generate_voiceover(text: str, output_path: str, video_type: str) -> dict:
    """
    video_type ('shorts'/'longform') is accepted explicitly so future
    per-format voice tuning (pacing, pitch) has a clear hook point —
    both formats currently share the same voice for brand consistency.
    Returns: {"path": str, "provider_used": str}
    """
    providers = [
        ("piper_local", lambda t, p: _piper_provider(t, p)),
        ("edge_tts", lambda t, p: _edge_tts_provider(t, p)),
        ("elevenlabs", lambda t, p: _elevenlabs_provider(t, p)),
    ]
    path, provider_used = run_with_fallback(providers, text, output_path)
    return {"path": path, "provider_used": provider_used}
