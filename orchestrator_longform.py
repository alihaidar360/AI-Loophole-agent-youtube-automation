"""
orchestrator_longform.py
Entry point for the 2x/week Long-form workflow (.github/workflows/longform_pipeline.yml).
"""

from core.pipeline_runner import run_pipeline

if __name__ == "__main__":
    run_pipeline(video_type="longform")
