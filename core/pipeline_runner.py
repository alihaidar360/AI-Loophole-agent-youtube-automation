"""
core/pipeline_runner.py
The heart of the system. Given a video_type ("shorts" or "longform"),
this either RESUMES an incomplete job or CREATES a new one, then walks
through every stage, persisting state after each successful step and
pausing (not crashing) on failure so the next scheduled run can retry.
"""

import os
import logging
from config import Config
from core import state_manager as sm
from core.fallback import AllProvidersFailedError
from modules import research, scripting, audio, visuals, captions, assembly, upload, topic_selector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipeline")


def _work_dir(job_id: str) -> str:
    return os.path.join(Config.ASSETS_DIR, job_id)


def run_pipeline(video_type: str):
    """video_type: 'shorts' or 'longform'"""
    os.makedirs(Config.STATE_DIR, exist_ok=True)
    os.makedirs(Config.ASSETS_DIR, exist_ok=True)

    # 1. Resume an incomplete job if one exists, else start a new one.
    incomplete = sm.get_incomplete_jobs(video_type)
    if incomplete:
        job = incomplete[0]
        job_id = job["job_id"]
        logger.info(f"Resuming existing job: {job_id} (paused at: {job.get('failed_step')})")
    else:
        topic = topic_selector.select_next_topic()
        job_id = sm.create_job(video_type, topic)
        job = sm.get_job(job_id)
        logger.info(f"Created new job: {job_id} for topic '{topic}'")

    work_dir = _work_dir(job_id)
    os.makedirs(work_dir, exist_ok=True)

    while True:
        job = sm.get_job(job_id)
        step = sm.next_step_for(job)
        if step is None:
            logger.info(f"Job {job_id}: all steps complete.")
            break

        logger.info(f"Job {job_id}: running step '{step}'")
        try:
            _run_step(step, job, work_dir, video_type)
        except AllProvidersFailedError as e:
            logger.error(f"Job {job_id}: step '{step}' failed on ALL providers: {e}")
            sm.mark_step_failed(job_id, step, str(e))
            logger.info("Pausing job. Next scheduled run will retry from this exact step.")
            return  # exit gracefully — do NOT crash the whole workflow
        except Exception as e:
            logger.error(f"Job {job_id}: unexpected error on step '{step}': {e}")
            sm.mark_step_failed(job_id, step, str(e))
            return

    # Successfully finished every step -> job is complete, archive it.
    sm.archive_job(job_id)
    logger.info(f"Job {job_id}: published and archived successfully.")


def _run_step(step: str, job: dict, work_dir: str, video_type: str):
    job_id = job["job_id"]
    topic = job["topic"]
    assets = job.get("assets", {})

    if step == "research":
        result = research.research_tool(topic)
        keywords = research.get_seo_keywords(topic, result["pain_points"])
        _save_json(os.path.join(work_dir, "research.json"), {**result, "seo_keywords": keywords})
        sm.mark_step_complete(job_id, step, {"research_path": os.path.join(work_dir, "research.json")})

    elif step == "script":
        research_data = _load_json(assets["research_path"])
        if video_type == "shorts":
            script = scripting.generate_shorts_script(research_data)
        else:
            script = scripting.generate_longform_script(research_data)
        script_path = os.path.join(work_dir, "script.json")
        _save_json(script_path, script)
        sm.mark_step_complete(job_id, step, {"script_path": script_path})

    elif step == "voiceover":
        script = _load_json(assets["script_path"])
        narration_text = _extract_narration_text(script, video_type)
        audio_path = os.path.join(work_dir, "voice.mp3")
        result = audio.generate_voiceover(narration_text, audio_path)
        sm.mark_step_complete(job_id, step, {
            "audio_path": result["path"],
            "narration_text": narration_text,  # stashed for captions step
        })

    elif step == "visuals":
        script = _load_json(assets["script_path"])
        visuals_dir = os.path.join(work_dir, "visuals")
        count = 4 if video_type == "shorts" else 10
        result = visuals.fetch_visuals(script["video_mood"], [job["topic"]], count, visuals_dir)
        music = visuals.select_background_music(script["video_mood"])
        sm.mark_step_complete(job_id, step, {
            "visual_paths": result["paths"],
            "accent_hex": result["accent_hex"],
            "music_path": music["path"],
        })

    elif step == "captions":
        caption_meta = captions.generate_captions(
            assets["audio_path"], video_type, assets["accent_hex"], work_dir
        )
        caption_meta_path = os.path.join(work_dir, "captions.json")
        _save_json(caption_meta_path, caption_meta)
        sm.mark_step_complete(job_id, step, {"caption_meta_path": caption_meta_path})

    elif step == "assembly":
        caption_meta = _load_json(assets["caption_meta_path"])
        output_path = os.path.join(work_dir, "final_video.mp4")
        assembly.assemble_video(
            voiceover_path=assets["audio_path"],
            visual_paths=assets["visual_paths"],
            caption_frames_meta=caption_meta,
            music_path=assets["music_path"],
            video_type=video_type,
            output_path=output_path,
        )
        sm.mark_step_complete(job_id, step, {"final_video_path": output_path})

    elif step == "upload":
        script = _load_json(assets["script_path"])
        thumb_bg = assets["visual_paths"][0]
        thumb_path = os.path.join(work_dir, "thumbnail.jpg")
        upload.generate_thumbnail(script["title"], assets["accent_hex"], thumb_bg, thumb_path)

        video_id = upload.upload_video(
            video_path=assets["final_video_path"],
            thumbnail_path=thumb_path,
            title=script["title"],
            description=script.get("description", ""),
            tags=script.get("tags", []),
            privacy_status="public",  # per explicit user instruction: auto-publish
        )
        sm.mark_job_completed(job_id, video_id)
        sm.mark_step_complete(job_id, step, {"youtube_video_id": video_id})
        logger.info(f"Published: https://youtube.com/watch?v={video_id}")


def _extract_narration_text(script: dict, video_type: str) -> str:
    if video_type == "shorts":
        return f"{script['hook']} {script['body']} {script.get('cta', '')}"
    return " ".join(ch["narration"] for ch in script["chapters"])


def _save_json(path: str, data: dict):
    import json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_json(path: str) -> dict:
    import json
    with open(path, "r") as f:
        return json.load(f)
