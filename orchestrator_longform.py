"""
orchestrator_longform.py
Entry point for the Long-form workflow. Triggered 2x/week.
"""
from core.pipeline_runner import run_pipeline

if __name__ == "__main__":
    run_pipeline(video_type="longform")
