"""
modules/assembly.py
Stage 6: Video Assembly Engine — Remotion bridge.
Builds a JSON props file describing the video's timeline (b-roll, audio,
captions, SFX cues, colors) and invokes Remotion's CLI to render the
final MP4. Remotion itself lives in /remotion (Node.js/React project).
"""

import json
import os
import subprocess
from config import Config


def assemble_video(video_type: str, audio_path: str, visual_paths: list,
                    caption_data: dict, sfx_cues: list, accent_hex: str,
                    music_path: str, total_duration: float, output_path: str) -> str:
    composition_id = "ShortsVideo" if video_type == "shorts" else "LongformVideo"
    canvas = (1080, 1920) if video_type == "shorts" else (1920, 1080)

    props = {
        "audioPath": os.path.abspath(audio_path),
        "visualPaths": [os.path.abspath(p) for p in visual_paths],
        "words": caption_data.get("words", []),
        "chunks": caption_data.get("chunks", []),
        # sound_design.py produces cues shaped like {"sfx_path": ..., "start_time": ...}
        # — read those exact keys here, output camelCase for the JS side.
        "sfxCues": [
            {"path": os.path.abspath(c["sfx_path"]), "startTime": c["start_time"]}
            for c in (sfx_cues or []) if c.get("sfx_path")
        ],
        "accentHex": accent_hex,
        "musicPath": os.path.abspath(music_path) if music_path else None,
        "durationInSeconds": total_duration,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    props_path = os.path.join(os.path.dirname(output_path), "remotion_props.json")
    with open(props_path, "w") as f:
        json.dump(props, f)

    cmd = [
        "npx", "remotion", "render",
        "src/index.jsx",
        composition_id,
        os.path.abspath(output_path),
        f"--props={props_path}",
        f"--width={canvas[0]}",
        f"--height={canvas[1]}",
    ]

    result = subprocess.run(
        cmd, cwd=Config.REMOTION_DIR, capture_output=True, text=True, timeout=1800
    )
    if result.returncode != 0:
        raise RuntimeError(f"Remotion render failed:\n{result.stderr[-3000:]}")

    if not os.path.exists(output_path):
        raise RuntimeError("Remotion did not produce an output file")

    return output_path
