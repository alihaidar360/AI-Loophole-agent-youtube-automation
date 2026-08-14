"""
modules/captions.py
Whisper-based transcription — produces word-level timestamps (for Shorts
kinetic captions) and sentence-level chunks (for Long-form subtitles).
This is the single source of truth pipeline_runner.py calls; the actual
PNG/visual rendering of captions happens in Remotion, not here — this
module only produces the timing DATA.
"""

import whisper

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def generate_caption_data(audio_path: str, video_type: str) -> dict:
    """
    audio_path: path to the voiceover mp3 (a plain string)
    video_type: 'shorts' or 'longform'

    Returns:
    {
        "words": [{"word": str, "start": float, "end": float}, ...],
        "chunks": [{"text": str, "start": float, "end": float}, ...],
    }
    Both "words" and "chunks" are always populated regardless of
    video_type, so callers can use whichever they need.
    """
    model = _get_model()
    result = model.transcribe(audio_path, word_timestamps=True)

    words = []
    chunks = []

    for segment in result.get("segments", []):
        chunks.append({
            "text": segment["text"].strip(),
            "start": segment["start"],
            "end": segment["end"],
        })
        for w in segment.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": w["start"],
                "end": w["end"],
            })

    return {"words": words, "chunks": chunks}
