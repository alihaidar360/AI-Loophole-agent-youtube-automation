"""
orchestrator_shorts.py
Entry point for the daily Shorts workflow (.github/workflows/shorts_pipeline.yml).
Called twice a day per the user's schedule (morning + evening) to produce
2 Shorts/day.
"""

from core.pipeline_runner import run_pipeline

if __name__ == "__main__":
    run_pipeline(video_type="shorts")
