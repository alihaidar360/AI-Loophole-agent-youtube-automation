"""
core/state_manager.py
Manages job_state.json (in-progress/resumable jobs) and published_log.json
(history of everything ever published, including backfilled pre-pipeline
videos). Both are plain JSON, committed to git as text — the only state
that survives across ephemeral GitHub Actions runs.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from config import Config

STEPS = ["research", "script", "voiceover", "visuals", "sound_design", "captions", "assembly", "upload"]


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
    jobs = _load_all_jobs()
    job_id = f"{video_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    jobs[job_id] = {
        "job_id": job_id,
        "video_type": video_type,
        "topic": topic,
        "status": "pending",
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
    jobs = _load_all_jobs()
    incomplete = [
        j for j in jobs.values()
        if j["video_type"] == video_type and j["status"] not in ("completed", "archived")
    ]
    return sorted(incomplete, key=lambda j: j["created_at"])


def get_job(job_id: str) -> dict:
    return _load_all_jobs()[job_id]


def next_step_for(job: dict) -> str:
    for step in STEPS:
        if step not in job["completed_steps"]:
            return step
    return None


def mark_step_complete(job_id: str, step: str, asset_updates: dict = None):
    jobs = _load_all_jobs()
    job = jobs[job_id]
    if step not in job["completed_steps"]:
        job["completed_steps"].append(step)
    job["status"] = f"step_{step}_done"
    job["failed_step"] = None
    if asset_updates:
        job["assets"].update(asset_updates)
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


def flag_needs_review(job_id: str, reason: str):
    jobs = _load_all_jobs()
    jobs[job_id]["needs_manual_review"] = True
    jobs[job_id]["review_reason"] = reason
    jobs[job_id]["last_updated"] = _now()
    _save_all_jobs(jobs)


def mark_job_completed(job_id: str, youtube_video_id: str, title: str = "",
                        privacy_status: str = "public", verdict_sentiment: str = "neutral"):
    jobs = _load_all_jobs()
    job = jobs[job_id]
    job["status"] = "completed"
    job["youtube_video_id"] = youtube_video_id
    job["last_updated"] = _now()
    _save_all_jobs(jobs)
    _append_published_log(job, title, privacy_status, verdict_sentiment)


def archive_job(job_id: str):
    jobs = _load_all_jobs()
    jobs[job_id]["status"] = "archived"
    jobs[job_id]["assets"] = {}
    _save_all_jobs(jobs)


def _load_published_log() -> list:
    if not os.path.exists(Config.PUBLISHED_LOG_FILE):
        return []
    with open(Config.PUBLISHED_LOG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_published_log(log: list):
    os.makedirs(Config.STATE_DIR, exist_ok=True)
    with open(Config.PUBLISHED_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def _append_published_log(job: dict, title: str, privacy_status: str, verdict_sentiment: str):
    log = _load_published_log()
    log.append({
        "job_id": job["job_id"],
        "topic": job["topic"],
        "title": title,
        "video_type": job["video_type"],
        "youtube_video_id": job.get("youtube_video_id"),
        "privacy_status": privacy_status,
        "verdict_sentiment": verdict_sentiment,
        "published_at": _now(),
        "backfilled": False,
    })
    _save_published_log(log)


def get_recently_covered_topics(video_type: str, lookback: int = 15) -> set:
    log = _load_published_log()
    same_format = [e for e in log if e.get("video_type") == video_type]
    recent = same_format[-lookback:]
    return {e["topic"] for e in recent if e.get("topic")}


def get_latest_published(video_type: str, only_public: bool = True) -> dict:
    """Used for cross-promotion: the most recent published video of a
    given type, so the other format can reference it by real title/link."""
    log = _load_published_log()
    candidates = [
        e for e in log if e.get("video_type") == video_type and e.get("youtube_video_id")
        and (not only_public or e.get("privacy_status", "public") == "public")
    ]
    if not candidates:
        return None
    latest = sorted(candidates, key=lambda e: e["published_at"])[-1]
    return {
        "title": latest.get("title") or latest.get("topic"),
        "video_id": latest["youtube_video_id"],
        "url": f"https://youtube.com/watch?v={latest['youtube_video_id']}",
    }
