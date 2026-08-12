"""
modules/assembly.py
Stage: Video Assembly Engine — Remotion-based (replaces the old MoviePy
static-crossfade renderer). Python's job here is just to build a clean
JSON "timeline" describing what happens when, then hand it to Remotion
(Node/React) to actually render — this is the JS boundary the pipeline
now crosses, exactly as discussed.

Both Shorts and Long-form get their own Remotion Composition
(ShortsVideo / LongformVideo — see remotion/src/compositions/) with
independently-tuned pacing; this module just prepares the right props
for whichever one is being rendered.
"""

import json
import os
import subprocess
from config import Config


def _build_visual_timeline(visual_paths: list, total_duration: float) -> list:
    """Distributes b-roll clips evenly across the runtime. Each entry
    becomes one Ken-Burns Sequence in Remotion."""
    if not visual_paths:
        return []
    per_clip = total_duration / len(visual_paths)
    timeline = []
    t = 0.0
    for path in visual_paths:
        timeline.append({"src": os.path.abspath(path), "start": round(t, 2), "duration": round(per_clip, 2)})
        t += per_clip
    return timeline


def build_props(video_type: str, audio_path: str, visual_paths: list,
                 caption_data: dict, sfx_cues: list, accent_hex: str,
                 music_path: str, total_duration: float) -> dict:
    """Assembles the full props object passed to the Remotion Composition."""
    timeline = {
        "visuals": _build_visual_timeline(visual_paths, total_duration),
        "sfxCues": [{"sfx": os.path.abspath(c["sfx"]), "time": c["time"], "volume": c["volume"]}
                    for c in sfx_cues if os.path.exists(c["sfx"])],
        "accentHex": accent_hex,
    }
    if video_type == "shorts":
        timeline["words"] = caption_data.get("words", [])
    else:
        timeline["chunks"] = caption_data.get("chunks", [])

    return {
        "audioSrc": os.path.abspath(audio_path),
        "musicSrc": os.path.abspath(music_path) if music_path and os.path.exists(music_path) else "",
        "durationInSeconds": total_duration,
        "timeline": timeline,
    }


def render_video(video_type: str, props: dict, output_path: str) -> str:
    """
    Calls the Remotion CLI to render the final MP4.
    Requires Node.js + `npm ci` already run inside remotion/ (handled by
    the GitHub Actions workflow before this step runs).
    """
    composition_id = "ShortsVideo" if video_type == "shorts" else "LongformVideo"
    remotion_dir = os.path.abspath(Config.REMOTION_DIR)

    props_path = os.path.abspath(os.path.join(os.path.dirname(output_path), "remotion_props.json"))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(props_path, "w") as f:
        json.dump(props, f)

    output_abs = os.path.abspath(output_path)

    cmd = [
        "npx", "remotion", "render",
        "src/index.jsx", composition_id, output_abs,
        f"--props={props_path}",
    ]
    result = subprocess.run(cmd, cwd=remotion_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Remotion render failed (composition={composition_id}).\n"
            f"stdout: {result.stdout[-2000:]}\nstderr: {result.stderr[-2000:]}"
        )
    if not os.path.exists(output_abs):
        raise RuntimeError("Remotion reported success but output file is missing.")
    return output_abs


def assemble_video(video_type: str, audio_path: str, visual_paths: list,
                    caption_data: dict, sfx_cues: list, accent_hex: str,
                    music_path: str, total_duration: float, output_path: str) -> str:
    """Main entry point for the assembly stage — builds props, renders,
    returns the final video path."""
    props = build_props(video_type, audio_path, visual_paths, caption_data,
                         sfx_cues, accent_hex, music_path, total_duration)
    return render_video(video_type, props, output_path)
