"""
orchestrator_shorts.py
Entry point for the daily Shorts workflow (.github/workflows/shorts_pipeline.yml).
"""

from core.pipeline_runner import run_pipeline

if __name__ == "__main__":
    run_pipeline(video_type="shorts")
