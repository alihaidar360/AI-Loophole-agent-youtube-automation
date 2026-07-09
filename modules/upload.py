"""
modules/upload.py
Stage 7: Publish Engine
Uploads the final video directly to YouTube (public, per user's choice)
using the YouTube Data API v3, with SEO-optimized title/description/tags
and an auto-generated thumbnail.
"""

import os
import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.http
from PIL import Image, ImageDraw, ImageFont
from config import Config


def _get_youtube_client():
    Config.validate(["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"])
    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=Config.YT_REFRESH_TOKEN,
        client_id=Config.YT_CLIENT_ID,
        client_secret=Config.YT_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def generate_thumbnail(title: str, accent_hex: str, background_image_path: str,
                        out_path: str) -> str:
    """Simple, clean Pillow-based thumbnail: background image + bold title text."""
    W, H = 1280, 720
    img = Image.open(background_image_path).convert("RGB").resize((W, H))
    draw = ImageDraw.Draw(img, "RGBA")

    # Dark gradient strip at the bottom for text readability
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, H * 0.6, W, H], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(Config.FONT_BOLD, 64)

    # Wrap title across 2 lines max, keep it punchy
    words = title.split()
    line1 = " ".join(words[: len(words) // 2 + 1])
    line2 = " ".join(words[len(words) // 2 + 1:])

    draw.text((60, H - 220), line1, font=font, fill=accent_hex)
    if line2:
        draw.text((60, H - 140), line2, font=font, fill="white")

    img.convert("RGB").save(out_path, quality=92)
    return out_path


def upload_video(video_path: str, thumbnail_path: str, title: str, description: str,
                  tags: list, category_id: str = "28",  # "28" = Science & Technology
                  privacy_status: str = "public") -> str:
    """
    Returns the published YouTube video ID.
    privacy_status: 'public' per user's explicit instruction (auto-publish).
    """
    youtube = _get_youtube_client()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = googleapiclient.http.MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()

    video_id = response["id"]

    if thumbnail_path and os.path.exists(thumbnail_path):
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=googleapiclient.http.MediaFileUpload(thumbnail_path),
        ).execute()

    return video_id
