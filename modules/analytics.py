"""
modules/analytics.py
Weekly feedback loop. Pulls retention/CTR data for the channel's videos
— including old ones published before this pipeline existed (via
backfill_from_channel) — and derives simple, explainable patterns fed
back into script generation.
"""

import json
import os
from collections import defaultdict
import google.oauth2.credentials
import googleapiclient.discovery
from config import Config
from core import state_manager as sm

MIN_VIDEOS_FOR_INSIGHTS = 10
STOPWORDS = {"the", "a", "an", "is", "are", "this", "that", "for", "with", "of",
             "to", "and", "in", "on", "i", "you", "your", "it", "how", "vs", "ai"}


def _get_clients():
    Config.validate(["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"])
    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=Config.YT_REFRESH_TOKEN,
        client_id=Config.YT_CLIENT_ID,
        client_secret=Config.YT_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    data_api = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    analytics_api = googleapiclient.discovery.build("youtubeAnalytics", "v2", credentials=creds)
    return data_api, analytics_api


def backfill_from_channel(data_api) -> int:
    """Pulls the channel's FULL upload history (including videos made
    before this pipeline existed) into published_log.json as backfilled
    entries, so old videos contribute to analytics instead of being invisible."""
    channel_resp = data_api.channels().list(part="contentDetails", mine=True).execute()
    items = channel_resp.get("items", [])
    if not items:
        return 0
    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    existing_log = sm._load_published_log()
    existing_ids = {e.get("youtube_video_id") for e in existing_log}

    added = 0
    next_page = None
    while True:
        resp = data_api.playlistItems().list(
            part="snippet", playlistId=uploads_playlist_id, maxResults=50, pageToken=next_page,
        ).execute()
        for item in resp.get("items", []):
            vid = item["snippet"]["resourceId"]["videoId"]
            if vid in existing_ids:
                continue
            existing_log.append({
                "job_id": None,
                "topic": "",
                "title": item["snippet"]["title"],
                "video_type": "unknown",
                "youtube_video_id": vid,
                "privacy_status": "public",
                "verdict_sentiment": None,
                "published_at": item["snippet"]["publishedAt"],
                "backfilled": True,
            })
            added += 1
        next_page = resp.get("nextPageToken")
        if not next_page:
            break

    sm._save_published_log(existing_log)
    return added


def _fetch_video_metrics(analytics_api, video_id: str) -> dict:
    try:
        response = analytics_api.reports().query(
            ids="channel==MINE",
            startDate="2020-01-01",
            endDate="today",
            metrics="averageViewPercentage,views,impressions,impressionsClickThroughRate",
            filters=f"video=={video_id}",
        ).execute()
        rows = response.get("rows", [])
        if not rows:
            return {}
        row = rows[0]
        return {
            "avg_view_pct": row[0],
            "views": row[1],
            "impressions": row[2] if len(row) > 2 else None,
            "ctr": row[3] if len(row) > 3 else None,
        }
    except Exception:
        return {}


def _derive_insights(enriched: list) -> dict:
    if len(enriched) < MIN_VIDEOS_FOR_INSIGHTS:
        return {"status": "insufficient_data", "videos_analyzed": len(enriched)}

    by_sentiment = defaultdict(list)
    by_title_keyword = defaultdict(list)

    for v in enriched:
        if v.get("avg_view_pct") is None:
            continue
        sentiment = v.get("verdict_sentiment")
        if sentiment:
            by_sentiment[sentiment].append(v["avg_view_pct"])

        for word in (v.get("title") or "").split():
            cleaned = word.strip(".,!?:;\"'()").lower()
            if len(cleaned) > 2 and cleaned not in STOPWORDS:
                by_title_keyword[cleaned].append(v["avg_view_pct"])

    def _best(group):
        averaged = {k: sum(vals) / len(vals) for k, vals in group.items() if len(vals) >= 2}
        return max(averaged, key=averaged.get) if averaged else None

    def _worst(group):
        averaged = {k: sum(vals) / len(vals) for k, vals in group.items() if len(vals) >= 2}
        return min(averaged, key=averaged.get) if averaged else None

    return {
        "status": "ok",
        "videos_analyzed": len(enriched),
        "includes_backfilled_history": any(v.get("backfilled") for v in enriched),
        "best_performing_sentiment": _best(by_sentiment),
        "best_performing_title_keyword": _best(by_title_keyword),
        "worst_performing_title_keyword": _worst(by_title_keyword),
    }


def run_weekly_analysis():
    data_api, analytics_api = _get_clients()
    backfill_from_channel(data_api)

    log = sm._load_published_log()
    recent = [e for e in log if e.get("youtube_video_id")][-30:]

    enriched = []
    for entry in recent:
        metrics = _fetch_video_metrics(analytics_api, entry["youtube_video_id"])
        if metrics:
            enriched.append({**entry, **metrics})

    insights = _derive_insights(enriched)

    os.makedirs(Config.STATE_DIR, exist_ok=True)
    with open(Config.PERFORMANCE_INSIGHTS_FILE, "w") as f:
        json.dump(insights, f, indent=2)

    return insights


def load_insights() -> dict:
    if not os.path.exists(Config.PERFORMANCE_INSIGHTS_FILE):
        return None
    with open(Config.PERFORMANCE_INSIGHTS_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return None
    return data if data.get("status") == "ok" else None


if __name__ == "__main__":
    result = run_weekly_analysis()
    print(json.dumps(result, indent=2))
