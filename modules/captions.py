"""
modules/captions.py
Stage: Caption Data Engine
Whisper (local, free) extracts word-level timestamps. Rendering itself now
happens in Remotion (see remotion/), so this module's job is purely to
produce clean timing DATA:
  - Shorts   -> word-level list (for kinetic, one-word-at-a-time captions)
  - Longform -> sentence-chunk list (for standard bottom-third subtitles)
Both formats get their own tailored grouping logic, not a shared shortcut.
"""

import whisper

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("base")
    return _whisper_model


def transcribe_with_timestamps(audio_path: str) -> list:
    model = _get_whisper_model()
    result = model.transcribe(audio_path, word_timestamps=True)
    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            words.append({"word": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)})
    return words


def _group_words_into_sentences(words: list, max_chars: int = 70) -> list:
    chunks = []
    current = []
    current_len = 0
    for w in words:
        current.append(w)
        current_len += len(w["word"]) + 1
        if current_len >= max_chars or w["word"].endswith((".", "!", "?")):
            chunks.append(current)
            current = []
            current_len = 0
    if current:
        chunks.append(current)

    return [
        {
            "text": " ".join(w["word"] for w in chunk),
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
        }
        for chunk in chunks
    ]


def generate_caption_data(audio_path: str, video_type: str) -> dict:
    """
    Returns format-specific caption data:
      shorts:   {"style": "kinetic", "words": [{word,start,end}, ...]}
      longform: {"style": "subtitle", "chunks": [{text,start,end}, ...]}
    """
    words = transcribe_with_timestamps(audio_path)
    if video_type == "shorts":
        return {"style": "kinetic", "words": words}
    else:
        return {"style": "subtitle", "chunks": _group_words_into_sentences(words)}
