"""
modules/upload.py
Stage 7: Publish Engine. Uploads the final video to YouTube with
SEO-optimized metadata and the generated thumbnail.
"""

import os
import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.http
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


def upload_video(video_path: str, thumbnail_path: str, title: str, description: str,
                  tags: list, category_id: str = "28", privacy_status: str = "public") -> str:
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
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=googleapiclient.http.MediaFileUpload(thumbnail_path),
            ).execute()
        except Exception as e:
            # Custom thumbnails require a phone-verified YouTube channel.
            # The video itself is already live at this point — don't fail
            # the whole job over a cosmetic thumbnail issue. YouTube will
            # just show an auto-generated thumbnail instead.
            print(f"Warning: could not set custom thumbnail (video is still live): {e}")

    return video_id
