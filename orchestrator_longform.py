"""
orchestrator_longform.py
Entry point for the long-form workflow (.github/workflows/longform_pipeline.yml).
Runs 2x/week per the user's schedule to produce deep-dive 12-15 min videos.
"""

from core.pipeline_runner import run_pipeline

if __name__ == "__main__":
    run_pipeline(video_type="longform")
