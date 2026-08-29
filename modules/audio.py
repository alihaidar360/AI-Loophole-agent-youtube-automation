"""
modules/audio.py
Stage 3: Voiceover Engine.
Priority: Piper TTS (local, offline) -> Edge-TTS (free streaming) ->
ElevenLabs (optional small free tier). No billing/account required for
the first two — the pipeline works fully even if ElevenLabs is skipped.
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


def _ensure_piper_model() -> str:
    os.makedirs(PIPER_MODEL_DIR, exist_ok=True)
    voice = Config.PIPER_VOICE  # e.g. "en_US-ryan-high"
    name, quality = voice.rsplit("-", 1)
    speaker = name.split("-", 1)[1] if "-" in name else name

    onnx_path = os.path.join(PIPER_MODEL_DIR, f"{voice}.onnx")
    json_path = os.path.join(PIPER_MODEL_DIR, f"{voice}.onnx.json")

    if not os.path.exists(onnx_path):
        _download(f"{PIPER_MODEL_URL_BASE}/{speaker}/{quality}/{voice}.onnx", onnx_path)
    if not os.path.exists(json_path):
        _download(f"{PIPER_MODEL_URL_BASE}/{speaker}/{quality}/{voice}.onnx.json", json_path)

    return onnx_path


def _download(url: str, out_path: str):
    r = requests.get(url, timeout=60, stream=True)
    r.raise_for_status()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


def _piper_provider(text: str, output_path: str) -> str:
    onnx_path = _ensure_piper_model()
    wav_path = output_path.rsplit(".", 1)[0] + ".wav"

    result = subprocess.run(
        ["python3", "-m", "piper", "--model", onnx_path, "--output_file", wav_path],
        input=text.encode("utf-8"), capture_output=True, timeout=300,
    )
    if result.returncode != 0 or not os.path.exists(wav_path):
        raise RuntimeError(f"Piper TTS failed: {result.stderr.decode(errors='ignore')}")

    subprocess.run(["ffmpeg", "-y", "-i", wav_path, output_path],
                    capture_output=True, timeout=60, check=True)
    os.remove(wav_path)

    if os.path.getsize(output_path) == 0:
        raise RuntimeError("Piper TTS produced an empty file")
    return output_path


def _edge_tts_provider(text: str, output_path: str) -> str:
    async def _run():
        communicate = edge_tts.Communicate(text, Config.EDGE_TTS_VOICE)
        await communicate.save(output_path)

    asyncio.run(_run())
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Edge-TTS produced an empty file")
    return output_path


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
    video_type ('shorts'/'longform') accepted for future per-format voice
    tuning; both currently share the same voice for brand consistency.
    Returns: {"path": str, "provider_used": str}
    """
    providers = [
        ("piper_local", lambda t, p: _piper_provider(t, p)),
        ("edge_tts", lambda t, p: _edge_tts_provider(t, p)),
        ("elevenlabs", lambda t, p: _elevenlabs_provider(t, p)),
    ]
    path, provider_used = run_with_fallback(providers, text, output_path)
    return {"path": path, "provider_used": provider_used}
