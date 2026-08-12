"""
core/pipeline_runner.py
The main orchestrator. Resumes an incomplete job or creates a new one,
then walks through every stage, persisting state after each success and
pausing (never crashing the whole workflow) on failure.

Both 'shorts' and 'longform' run through this exact same orchestrator —
the per-format differences live inside each module (scripting persona,
Ken Burns intensity, caption style, sfx density, thumbnail layout), not
in two divergent code paths here. This keeps both formats maintained
with equal rigor by construction.
"""

import os
import json
import logging
from config import Config
from core import state_manager as sm
from core.fallback import AllProvidersFailedError
from modules import (research, scripting, audio, visuals, sound_design,
                      captions, assembly, thumbnail, upload, topic_selector, analytics)
from core import quality_gate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipeline")


def _work_dir(job_id: str) -> str:
    return os.path.join(Config.ASSETS_DIR, job_id)


def run_pipeline(video_type: str):
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
    fmt = Config.FORMATS[video_type]

    if step == "research":
        result = research.research_tool(topic)
        keywords = research.get_seo_keywords(topic, result["pain_points"])
        path = os.path.join(work_dir, "research.json")
        _save_json(path, {**result, "seo_keywords": keywords})
        sm.mark_step_complete(job_id, step, {"research_path": path})

    elif step == "script":
        research_data = _load_json(assets["research_path"])

        # Feature #2: cross-promotion — Shorts reference the latest public
        # long-form video by its real title, so the CTA points somewhere
        # real instead of a generic "subscribe".
        cross_promo = None
        if video_type == "shorts":
            cross_promo = sm.get_latest_published("longform")

        # Feature #1: analytics feedback loop — inject what's actually
        # worked on this channel recently, if enough data exists yet.
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
        sm.mark_step_complete(job_id, step, {
            "audio_path": result["path"],
            "narration_text": narration_text,
        })

    elif step == "visuals":
        script = _load_json(assets["script_path"])
        visuals_dir = os.path.join(work_dir, "visuals")
        os.makedirs(visuals_dir, exist_ok=True)
        mood_profile = visuals.get_mood_profile(script["video_mood"])

        # Per-format visual sourcing: Shorts get fewer, punchier clips;
        # Long-form pulls one query PER CHAPTER so footage stays specific
        # to what's being said, not one generic query for the whole video.
        all_paths = []
        if video_type == "shorts":
            query = f"{job['topic']} {mood_profile['keywords'][0]}"
            result = visuals.fetch_visuals_for_query(query, 5, visuals_dir)
            all_paths = result["paths"]
        else:
            for i, chapter in enumerate(script["chapters"]):
                chapter_keywords = " ".join(chapter["heading"].split()[:3])
                query = f"{job['topic']} {chapter_keywords}"
                try:
                    result = visuals.fetch_visuals_for_query(query, 2, visuals_dir)
                    all_paths.extend(result["paths"])
                except Exception:
                    # one chapter's specific query failing shouldn't kill the
                    # whole video — fall back to the generic mood query
                    fallback = visuals.fetch_visuals_for_query(
                        f"{job['topic']} {mood_profile['keywords'][0]}", 2, visuals_dir)
                    all_paths.extend(fallback["paths"])

        music = visuals.select_background_music(script["video_mood"])
        sm.mark_step_complete(job_id, step, {
            "visual_paths": all_paths,
            "accent_hex": mood_profile["accent_hex"],
            "music_path": music["path"],
        })

    elif step == "sound_design":
        # depends on caption timing, so this runs the transcription early;
        # captions step re-uses the same cached data rather than re-running Whisper
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
            # approximate chapter start times by splitting duration evenly
            # across chapters (each chapter's narration length already
            # roughly proportional to its spoken time)
            n_chapters = len(script["chapters"])
            chapters_with_times = [
                {"heading": ch["heading"], "start": (total_duration / n_chapters) * i}
                for i, ch in enumerate(script["chapters"])
            ]
            cues = sound_design.generate_sound_cues(video_type, total_duration, caption_data,
                                                     chapters_with_times)

        sm.mark_step_complete(job_id, step, {
            "caption_data_path": caption_path,
            "sound_cues": cues,
            "total_duration": total_duration,
        })

    elif step == "captions":
        # caption data was already generated in sound_design (needed for
        # cue timing) — this step just confirms it's present so the state
        # machine has an explicit checkpoint to resume from if assembly fails.
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

    elif step == "thumbnail":
        script = _load_json(assets["script_path"])
        thumb_path = os.path.join(work_dir, "thumbnail.png")
        thumbnail.generate_thumbnail(
            video_type=video_type,
            headline=script["thumbnail_headline"],
            tool_name=job["topic"],
            sentiment=script.get("verdict_sentiment", "neutral"),
            out_path=thumb_path,
        )
        sm.mark_step_complete(job_id, step, {"thumbnail_path": thumb_path})

    elif step == "upload":
        script = _load_json(assets["script_path"])
        research_data = _load_json(assets["research_path"])

        # Feature #3: quality gate — weak-source videos publish unlisted
        # instead of public, so a shaky research/script fallback never
        # silently drags down the channel's average performance.
        gate = quality_gate.evaluate(
            research_source=research_data.get("source", "unknown"),
            script_provider=script.get("_provider_used", "unknown"),
            script=script,
        )
        if gate["publish_as"] == "unlisted":
            logger.warning(f"Job {job_id}: {gate['reason']}")
            sm.flag_needs_review(job_id, gate["reason"])

        video_id = upload.upload_video(
            video_path=assets["final_video_path"],
            thumbnail_path=assets["thumbnail_path"],
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


def _extract_narration_text(script: dict, video_type: str) -> str:
    if video_type == "shorts":
        return f"{script['hook']} {script['body']} {script.get('cta', '')}"
    return " ".join(ch["narration"] for ch in script["chapters"])


def _save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_json(path: str):
    with open(path, "r") as f:
        return json.load(f)
