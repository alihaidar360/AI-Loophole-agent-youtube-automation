"""
modules/assembly.py
Stage 6: Video Assembly Engine
Combines: b-roll/visuals + voiceover + caption PNG overlays + background music
into the final MP4. Uses only ImageClip/VideoFileClip/AudioFileClip from
MoviePy — never TextClip, so ImageMagick is never invoked.
"""

import os
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips, vfx,
)
from config import Config


def _build_broll_track(visual_paths: list, target_duration: float, canvas_size: tuple):
    """Loops/trims b-roll clips (video or still image) to fill target_duration,
    resizing to canvas and applying a simple crossfade transition between clips."""
    clips = []
    per_clip_duration = target_duration / max(len(visual_paths), 1)

    for path in visual_paths:
        if path.lower().endswith((".mp4", ".mov", ".webm")):
            clip = VideoFileClip(path)
            if clip.duration < per_clip_duration:
                clip = clip.fx(vfx.loop, duration=per_clip_duration)
            else:
                clip = clip.subclip(0, per_clip_duration)
        else:
            clip = ImageClip(path).set_duration(per_clip_duration)

        clip = clip.resize(height=canvas_size[1]).crop(
            x_center=clip.w / 2, width=canvas_size[0]
        ) if clip.w >= canvas_size[0] else clip.resize(canvas_size)

        clip = clip.crossfadein(0.4).crossfadeout(0.4)
        clips.append(clip)

    return concatenate_videoclips(clips, method="compose", padding=-0.4)


def _overlay_caption_clips(base_video, caption_frames_meta: list):
    """caption_frames_meta: list of (image_path, start_time, duration)"""
    overlays = [base_video]
    for img_path, start, duration in caption_frames_meta:
        clip = (ImageClip(img_path)
                 .set_start(start)
                 .set_duration(duration)
                 .set_position("center"))
        overlays.append(clip)
    return CompositeVideoClip(overlays, size=base_video.size)


def assemble_video(voiceover_path: str, visual_paths: list, caption_frames_meta: list,
                    music_path: str, video_type: str, output_path: str) -> str:
    canvas_size = Config.SHORTS_SIZE if video_type == "shorts" else Config.LONGFORM_SIZE

    narration = AudioFileClip(voiceover_path)
    total_duration = narration.duration

    broll = _build_broll_track(visual_paths, total_duration, canvas_size)
    broll = broll.set_duration(total_duration)

    composed = _overlay_caption_clips(broll, caption_frames_meta)

    # Background music: quiet under the narration, never overpowering it.
    audio_tracks = [narration]
    if music_path and os.path.exists(music_path):
        music = AudioFileClip(music_path).volumex(0.12)
        if music.duration < total_duration:
            music = music.fx(vfx.loop, duration=total_duration)
        else:
            music = music.subclip(0, total_duration)
        audio_tracks.append(music)

    final_audio = CompositeAudioClip(audio_tracks)
    final_video = composed.set_audio(final_audio).set_duration(total_duration)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
    )

    # Close clips to free memory/file handles on the CI runner
    for c in [narration, broll, composed, final_video]:
        try:
            c.close()
        except Exception:
            pass

    return output_path
