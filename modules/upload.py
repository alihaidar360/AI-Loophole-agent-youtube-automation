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
    """Only used for Long-form videos. Creates a clean 16:9 thumbnail."""
    # Agar galti se video file pass ho jaye long video me bhi, toh crash na ho
    if not background_image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        print(f"[Warning] Invalid image for thumbnail: {background_image_path}. Skipping thumbnail generation.")
        return None

    W, H = 1280, 720
    img = Image.open(background_image_path).convert("RGB").resize((W, H))
    draw = ImageDraw.Draw(img, "RGBA")

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([0, H * 0.6, W, H], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(Config.FONT_BOLD, 64)
    except Exception:
        font = ImageFont.load_default()

    words = title.split()
    line1 = " ".join(words[: len(words) // 2 + 1])
    line2 = " ".join(words[len(words) // 2 + 1:])

    draw.text((60, H - 220), line1, font=font, fill=accent_hex)
    if line2:
        draw.text((60, H - 140), line2, font=font, fill="white")

    img.convert("RGB").save(out_path, quality=92)
    return out_path


def upload_video(video_path: str, thumbnail_path: str = None, title: str = "", description: str = "",
                  tags: list = None, category_id: str = "28",
                  privacy_status: str = "public") -> str:
    """
    Uploads long or short videos. 
    For Shorts: Pass thumbnail_path=None to skip thumbnail completely and rely purely on SEO/Keywords.
    """
    youtube = _get_youtube_client()

    # Dynamic SEO Tags formatting (Handles string or list inputs safely)
    if isinstance(tags, str):
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        tags_list = [str(t) for t in tags]
    else:
        tags_list = []

    body = {
        "snippet": {
            "title": (title or "Untitled")[:100],
            "description": (description or "")[:5000],
            "tags": tags_list[:50],  # YouTube API tags array limit wrapper
            "categoryId": str(category_id),
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

    # Thumbnail process (Only triggers for Long form if valid path is provided)
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=googleapiclient.http.MediaFileUpload(thumbnail_path),
            ).execute()
        except Exception as e:
            print(f"[Warning] Video uploaded successfully, but custom thumbnail skipped: {e}")

    return video_id