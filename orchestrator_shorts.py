"""
orchestrator_shorts.py
Entry point for the daily Shorts workflow. Triggered 2x/day.
"""
from core.pipeline_runner import run_pipeline

if __name__ == "__main__":
    run_pipeline(video_type="shorts")
