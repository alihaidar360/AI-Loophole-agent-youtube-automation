"""
modules/captions.py
Whisper-based transcription — word-level timestamps (Shorts kinetic
captions) and sentence-level chunks (Long-form subtitles). The actual
visual rendering happens in Remotion; this module only produces timing DATA.
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
    video_type: 'shorts' or 'longform' (accepted for symmetry with other
    stages; transcription itself doesn't currently branch on it)

    Returns: {"words": [{"word","start","end"}, ...], "chunks": [{"text","start","end"}, ...]}
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
