"""
core/state_manager.py
Manages job_state.json — the "database" that survives across ephemeral
GitHub Actions runs. Every job (one video) gets a unique job_id and a
status that tracks exactly which pipeline step it's on.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from config import Config

STEPS_SHORTS = ["research", "script", "voiceover", "visuals", "captions", "assembly", "upload"]
STEPS_LONGFORM = ["research", "script", "voiceover", "visuals", "captions", "assembly", "upload"]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_all_jobs():
    if not os.path.exists(Config.JOB_STATE_FILE):
        return {}
    with open(Config.JOB_STATE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_all_jobs(jobs: dict):
    os.makedirs(Config.STATE_DIR, exist_ok=True)
    with open(Config.JOB_STATE_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def create_job(video_type: str, topic: str) -> str:
    """video_type: 'shorts' or 'longform'"""
    jobs = _load_all_jobs()
    job_id = f"{video_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    jobs[job_id] = {
        "job_id": job_id,
        "video_type": video_type,
        "topic": topic,
        "status": "pending",
        "current_step": None,
        "completed_steps": [],
        "failed_step": None,
        "error_log": [],
        "assets": {},
        "created_at": _now(),
        "last_updated": _now(),
    }
    _save_all_jobs(jobs)
    return job_id


def get_incomplete_jobs(video_type: str) -> list:
    """Returns jobs that are not yet 'completed' — used to resume before
    starting a brand new job. Oldest first."""
    jobs = _load_all_jobs()
    incomplete = [
        j for j in jobs.values()
        if j["video_type"] == video_type and j["status"] not in ("completed", "archived")
    ]
    return sorted(incomplete, key=lambda j: j["created_at"])


def mark_step_complete(job_id: str, step: str, asset_paths: dict = None):
    jobs = _load_all_jobs()
    job = jobs[job_id]
    if step not in job["completed_steps"]:
        job["completed_steps"].append(step)
    job["current_step"] = step
    job["status"] = f"step_{step}_done"
    job["failed_step"] = None
    if asset_paths:
        job["assets"].update(asset_paths)
    job["last_updated"] = _now()
    _save_all_jobs(jobs)


def mark_step_failed(job_id: str, step: str, error_msg: str):
    jobs = _load_all_jobs()
    job = jobs[job_id]
    job["status"] = "paused_on_error"
    job["failed_step"] = step
    job["error_log"].append({"step": step, "error": str(error_msg), "time": _now()})
    job["last_updated"] = _now()
    _save_all_jobs(jobs)


def mark_job_completed(job_id: str, youtube_video_id: str):
    jobs = _load_all_jobs()
    job = jobs[job_id]
    job["status"] = "completed"
    job["youtube_video_id"] = youtube_video_id
    job["last_updated"] = _now()
    _save_all_jobs(jobs)
    _append_published_log(job)


def _append_published_log(job: dict):
    log = []
    if os.path.exists(Config.PUBLISHED_LOG_FILE):
        with open(Config.PUBLISHED_LOG_FILE, "r") as f:
            try:
                log = json.load(f)
            except json.JSONDecodeError:
                log = []
    log.append({
        "job_id": job["job_id"],
        "topic": job["topic"],
        "video_type": job["video_type"],
        "youtube_video_id": job.get("youtube_video_id"),
        "published_at": _now(),
    })
    with open(Config.PUBLISHED_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def get_job(job_id: str) -> dict:
    return _load_all_jobs()[job_id]


def next_step_for(job: dict) -> str:
    """Given a job's completed_steps, figure out which step to run next."""
    all_steps = STEPS_SHORTS if job["video_type"] == "shorts" else STEPS_LONGFORM
    for step in all_steps:
        if step not in job["completed_steps"]:
            return step
    return None  # all steps done


def archive_job(job_id: str):
    """Cleanup after successful publish — keeps repo size under control."""
    jobs = _load_all_jobs()
    jobs[job_id]["status"] = "archived"
    jobs[job_id]["assets"] = {}  # drop asset paths, binaries are cache-only anyway
    _save_all_jobs(jobs)
