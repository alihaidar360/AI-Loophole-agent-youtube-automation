"""
modules/assembly.py
Stage 6: Video Assembly Engine — Remotion bridge.
Builds a JSON props file describing the video's timeline (b-roll, audio,
captions, SFX cues, colors) and invokes Remotion's CLI to render the
final MP4. Remotion itself lives in /remotion (Node.js/React project).

IMPORTANT: Remotion's renderer refuses file:// URLs for security reasons
("Not allowed to load local )


def assemble_video(video_type: str, audio_path: str, visual_paths: list,
                    caption_data: dict, sfx_cues: list, accent_hex: str,
                    music_path: str, total_duration: float, output_path: str) -> str:
    composition_id = "ShortsVideo" if video_type == "shorts" else "LongformVideo"
    canvas = (1080, 1920) if video_type == "shorts" else (1920, 1080)

    if not audio_path or not os.path.exists(audio_path):
        raise RuntimeError(f"Voiceover file missing on disk (stale cache?): {audio_path}")

    safe_visual_paths = [p for p in (visual_paths or []) if p and os.path.exists(p)]
    if not safe_visual_paths:
        raise RuntimeError("No visual files exist on disk (stale cache?) — cannot assemble video")

    # Defensive check: a path recorded in job_state.json doesn't guarantee
    # the actual binary still exists on disk (GitHub Actions cache can be
    # evicted/stale across a job resumed over multiple days/runs). Better
    # to silently skip music/SFX than crash the whole video over it.
    safe_music_path = music_path if music_path and os.path.exists(music_path) else None

    props = {
        "audioPath": _rel_to_assets(audio_path),
        "visualPaths": [_rel_to_assets(p) for p in safe_visual_paths],
        "words": caption_data.get("words", []),
        "chunks": caption_data.get("chunks", []),
        # sound_design.py produces cues shaped like {"sfx_path": ..., "start_time": ...}
        "sfxCues": [
            {"path": _rel_to_assets(c["sfx_path"]), "startTime": c["start_time"]}
            for c in (sfx_cues or [])
            if c.get("sfx_path") and os.path.exists(c["sfx_path"])
        ],
        "accentHex": accent_hex,
        "musicPath": _rel_to_assets(safe_music_path) if safe_music_path else None,
        "durationInSeconds": total_duration,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    props_path = os.path.abspath(
        os.path.join(os.path.dirname(output_path), "remotion_props.json")
    )
    with open(props_path, "w") as f:
        json.dump(props, f)

    cmd = [
        "npx", "remotion", "render",
        "src/Root.jsx",
        composition_id,
        os.path.abspath(output_path),
        f"--props={props_path}",
        f"--width={canvas[0]}",
        f"--height={canvas[1]}",
        f"--public-dir={ASSETS_ROOT}",
    ]

    result = subprocess.run(
        cmd, cwd="remotion", capture_output=True, text=True, timeout=1800
    )
    if result.returncode != 0:
        raise RuntimeError(f"Remotion render failed:\n{result.stderr[-3000:]}")

    if not os.path.exists(output_path):
        raise RuntimeError("Remotion did not produce an output file")

    return output_path
