"""
core/pipeline_runner.py
The heart of the system. Resumes an incomplete job or creates a new one,
then walks through every stage, persisting state after each successful
step and pausing (not crashing) on failure so the next scheduled run
retries from exactly where it left off.
"""

import json
import os
import subprocess
import logging
from config import Config
from core import state_manager as sm
from core import quality_gate
from core.fallback import AllProvidersFailedError
from modules import (research, scripting, audio, visuals, sound_design,
                      captions, assembly, thumbnail, upload, topic_selector, analytics)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipeline")


def _work_dir(job_id: str) -> str:
    return os.path.join(Config.ASSETS_DIR, job_id)


def _save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_json(path: str):
    with open(path, "r") as f:
        return json.load(f)


def _extract_narration_text(script: dict, video_type: str) -> str:
    if video_type == "shorts":
        return f"{script['hook']} {script['body']} {script.get('cta', '')}"
    return " ".join(ch["narration"] for ch in script["chapters"])


def _grab_video_frame(video_path: str, out_path: str) -> str:
    """Extracts a still frame from an mp4 for use as a thumbnail
    background. Returns None if extraction fails (thumbnail.py falls
    back to a plain dark background in that case — never crashes)."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-ss", "00:00:01", "-vframes", "1", out_path],
            capture_output=True, timeout=30, check=True,
        )
        return out_path if os.path.exists(out_path) else None
    except Exception:
        return None


def run_pipeline(video_type: str):
    """video_type: 'shorts' or 'longform'"""
    os.makedirs(Config.STATE_DIR, exist_ok=True)
    os.makedirs(Config.ASSETS_DIR, exist_ok=True)

    incomplete = sm.get_incomplete_jobs(video_type)
    if incomplete:
        job = incomplete[0]
        job_id = job["job_id"]
        logger.info(f"Resuming existing {video_type} job: {job_id} (paused at: {job.get('failed_step')})")
    else:
        topic = topic_selector.select_next_topic(video_type)
        job_id = sm.create_job(video_type, topic)
        logger.info(f"Created new {video_type} job: {job_id} for topic '{topic}'")

    work_dir = _work_dir(job_id)
    os.makedirs(work_dir, exist_ok=True)

    while True:
        job = sm.get_job(job_id)
        step = sm.next_step_for(job)
        if step is None:
            logger.info(f"Job {job_id}: all steps complete.")
            break

        logger.info(f"Job {job_id} [{video_type}]: running step '{step}'")
        try:
            _run_step(step, job, work_dir, video_type)
        except AllProvidersFailedError as e:
            logger.error(f"Job {job_id}: step '{step}' failed on ALL providers: {e}")
            sm.mark_step_failed(job_id, step, str(e))
            return
        except Exception as e:
            logger.error(f"Job {job_id}: unexpected error on step '{step}': {e}")
            sm.mark_step_failed(job_id, step, str(e))
            return

    sm.archive_job(job_id)
    logger.info(f"Job {job_id}: published and archived successfully.")


def _run_step(step: str, job: dict, work_dir: str, video_type: str):
    job_id = job["job_id"]
    topic = job["topic"]
    assets = job.get("assets", {})

    if step == "research":
        result = research.research_tool(topic)
        keywords = research.get_seo_keywords(topic, result["pain_points"])
        path = os.path.join(work_dir, "research.json")
        _save_json(path, {**result, "seo_keywords": keywords})
        sm.mark_step_complete(job_id, step, {"research_path": path})

    elif step == "script":
        research_data = _load_json(assets["research_path"])

        cross_promo = None
        if video_type == "shorts":
            cross_promo = sm.get_latest_published("longform")

        performance_insights = analytics.load_insights()

        script = (scripting.generate_shorts_script(research_data, cross_promo, performance_insights)
                  if video_type == "shorts"
                  else scripting.generate_longform_script(research_data, cross_promo, performance_insights))
        path = os.path.join(work_dir, "script.json")
        _save_json(path, script)
        sm.mark_step_complete(job_id, step, {"script_path": path})

    elif step == "voiceover":
        script = _load_json(assets["script_path"])
        narration_text = _extract_narration_text(script, video_type)
        audio_path = os.path.join(work_dir, "voice.mp3")
        result = audio.generate_voiceover(narration_text, audio_path, video_type)
        sm.mark_step_complete(job_id, step, {"audio_path": result["path"]})

    elif step == "visuals":
        script = _load_json(assets["script_path"])
        visuals_dir = os.path.join(work_dir, "visuals")

        if video_type == "shorts":
            result = visuals.fetch_visuals(script["video_mood"], [topic], 4, visuals_dir)
            visual_paths = result["paths"]
            accent_hex = result["accent_hex"]
        else:
            visual_paths = []
            for chapter in script["chapters"]:
                query = f"{topic} {chapter['heading']}"
                r = visuals.fetch_visuals_for_query(query, 2, visuals_dir)
                visual_paths.extend(r["paths"])
            accent_hex = visuals.get_mood_profile(script["video_mood"])["accent_hex"]

        music = visuals.select_background_music(script["video_mood"])
        sm.mark_step_complete(job_id, step, {
            "visual_paths": visual_paths,
            "accent_hex": accent_hex,
            "music_path": music["path"],
        })

    elif step == "sound_design":
        caption_data = captions.generate_caption_data(assets["audio_path"], video_type)
        caption_path = os.path.join(work_dir, "captions.json")
        _save_json(caption_path, caption_data)

        if video_type == "shorts":
            total_duration = caption_data["words"][-1]["end"] if caption_data["words"] else 50.0
            cues = sound_design.generate_sound_cues(video_type, total_duration, caption_data)
        else:
            script = _load_json(assets["script_path"])
            chunks = caption_data.get("chunks", [])
            total_duration = chunks[-1]["end"] if chunks else 660.0
            n_chapters = len(script["chapters"])
            chapters_with_times = [
                {"heading": ch["heading"], "start": (total_duration / n_chapters) * i}
                for i, ch in enumerate(script["chapters"])
            ]
            cues = sound_design.generate_sound_cues(video_type, total_duration, caption_data, chapters_with_times)

        sm.mark_step_complete(job_id, step, {
            "caption_data_path": caption_path,
            "sound_cues": cues,
            "total_duration": total_duration,
        })

    elif step == "captions":
        # caption data was already generated in sound_design (needed for
        # cue timing) — this is just an explicit checkpoint to resume from.
        assert os.path.exists(assets["caption_data_path"])
        sm.mark_step_complete(job_id, step, {})

    elif step == "assembly":
        caption_data = _load_json(assets["caption_data_path"])
        output_path = os.path.join(work_dir, "final_video.mp4")
        assembly.assemble_video(
            video_type=video_type,
            audio_path=assets["audio_path"],
            visual_paths=assets["visual_paths"],
            caption_data=caption_data,
            sfx_cues=assets["sound_cues"],
            accent_hex=assets["accent_hex"],
            music_path=assets["music_path"],
            total_duration=assets["total_duration"],
            output_path=output_path,
        )
        sm.mark_step_complete(job_id, step, {"final_video_path": output_path})

    elif step == "upload":
        script = _load_json(assets["script_path"])
        research_data = _load_json(assets["research_path"])

        gate = quality_gate.evaluate(
            research_source=research_data.get("source", "unknown"),
            script_provider=script.get("_provider_used", "unknown"),
            script=script,
        )
        if gate["publish_as"] == "unlisted":
            logger.warning(f"Job {job_id}: {gate['reason']}")
            sm.flag_needs_review(job_id, gate["reason"])

        thumb_frame_path = os.path.join(work_dir, "thumb_frame.jpg")
        first_visual = assets["visual_paths"][0] if assets.get("visual_paths") else None
        bg_path = None
        if first_visual and first_visual.lower().endswith((".mp4", ".mov", ".webm")):
            bg_path = _grab_video_frame(first_visual, thumb_frame_path)
        elif first_visual:
            bg_path = first_visual

        thumb_path = os.path.join(work_dir, "thumbnail.jpg")
        thumbnail.generate_thumbnail(
            headline=script.get("thumbnail_headline", script["title"]),
            verdict_sentiment=script.get("verdict_sentiment", "neutral"),
            background_image_path=bg_path,
            out_path=thumb_path,
        )

        video_id = upload.upload_video(
            video_path=assets["final_video_path"],
            thumbnail_path=thumb_path,
            title=script["title"],
            description=script.get("description", ""),
            tags=script.get("tags", []),
            privacy_status=gate["publish_as"],
        )
        sm.mark_job_completed(
            job_id, video_id,
            title=script["title"],
            privacy_status=gate["publish_as"],
            verdict_sentiment=script.get("verdict_sentiment", "neutral"),
        )
        sm.mark_step_complete(job_id, step, {"youtube_video_id": video_id})
        logger.info(f"Published ({gate['publish_as']}): https://youtube.com/watch?v={video_id}")
