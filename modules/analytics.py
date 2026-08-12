"""
modules/analytics.py
Add #1 (Analytics Feedback Loop) — the piece that makes the channel
actually learn instead of producing every video the same way forever.

Runs weekly (separate workflow, not the daily/2x-week content pipelines).
Pulls retention/CTR data for recently published videos via the YouTube
Analytics API, derives simple actionable patterns, and writes them to
pipeline_state/performance_insights.json — which scripting.py then reads
and injects into future prompts.

Needs an extra OAuth scope (yt-analytics.readonly) on top of the upload
scope already set up in Phase 3 of the setup guide — see README.
"""

import json
import os
from collections import defaultdict
import google.oauth2.credentials
import googleapiclient.discovery
from config import Config

MIN_VIDEOS_FOR_INSIGHTS = 10  # below this, data is too noisy to act on


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


def _load_published_log() -> list:
    if not os.path.exists(Config.PUBLISHED_LOG_FILE):
        return []
    with open(Config.PUBLISHED_LOG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _fetch_video_metrics(analytics_api, video_id: str) -> dict:
    """Pulls the metrics that actually matter for 'what's working':
    average view percentage (retention) and CTR both come from this
    single report, keyed by video."""
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
        # A single video's analytics failing (e.g. too new, no data yet)
        # shouldn't kill the whole weekly analysis.
        return {}


STOPWORDS = {"the", "a", "an", "is", "are", "this", "that", "for", "with", "of",
             "to", "and", "in", "on", "i", "you", "your", "it", "how", "vs", "ai"}


def _derive_insights(enriched: list) -> dict:
    """Very simple, explainable pattern-finding — not ML, just grouped
    averages. Intentionally conservative: only surfaces a pattern if
    there's a real enough gap to act on.

    Uses TITLE words (not the internal 'topic' field) for keyword
    grouping, because backfilled/old videos (manually published, or from
    before this feedback loop existed) always have a title but never have
    a 'topic' — this is what lets old videos actually contribute signal
    instead of being counted but ignored."""
    if len(enriched) < MIN_VIDEOS_FOR_INSIGHTS:
        return {"status": "insufficient_data", "videos_analyzed": len(enriched)}

    by_sentiment = defaultdict(list)
    by_title_keyword = defaultdict(list)

    for v in enriched:
        if v.get("avg_view_pct") is None:
            continue
        sentiment = v.get("verdict_sentiment")
        if sentiment:  # only pipeline-generated videos have this
            by_sentiment[sentiment].append(v["avg_view_pct"])

        title = v.get("title") or ""
        for word in title.split():
            cleaned = word.strip(".,!?:;\"'()").lower()
            if len(cleaned) > 2 and cleaned not in STOPWORDS:
                by_title_keyword[cleaned].append(v["avg_view_pct"])

    def _best(group: dict) -> str:
        averaged = {k: sum(vals) / len(vals) for k, vals in group.items() if len(vals) >= 2}
        if not averaged:
            return None
        return max(averaged, key=averaged.get)

    def _worst(group: dict) -> str:
        averaged = {k: sum(vals) / len(vals) for k, vals in group.items() if len(vals) >= 2}
        if not averaged:
            return None
        return min(averaged, key=averaged.get)

    return {
        "status": "ok",
        "videos_analyzed": len(enriched),
        "includes_backfilled_history": any(v.get("backfilled") for v in enriched),
        "best_performing_sentiment": _best(by_sentiment),
        "best_performing_title_keyword": _best(by_title_keyword),
        "worst_performing_title_keyword": _worst(by_title_keyword),
    }


def _get_uploads_playlist_id(data_api) -> str:
    response = data_api.channels().list(part="contentDetails", mine=True).execute()
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def backfill_from_channel(data_api, analytics_api) -> list:
    """
    Pulls EVERY video already on the channel directly from YouTube — not
    just ones this pipeline tracked in published_log.json. This matters
    because the first batch of videos (published before this feedback
    loop existed, or uploaded manually) would otherwise be invisible to
    the analysis even though YouTube has full analytics data for them.

    Returns a list of {video_id, title, published_at} for every video
    found, and merges any missing ones into published_log.json so
    future runs (and the rest of the pipeline) see them too.
    """
    uploads_playlist_id = _get_uploads_playlist_id(data_api)

    all_videos = []
    next_page_token = None
    while True:
        response = data_api.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        ).execute()
        for item in response.get("items", []):
            snippet = item["snippet"]
            all_videos.append({
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "published_at": snippet["publishedAt"],
            })
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    _merge_into_published_log(all_videos)
    return all_videos


def _merge_into_published_log(channel_videos: list):
    """Adds any channel video not already present in published_log.json —
    tagged as 'backfilled' since we don't know its original video_type,
    topic, or verdict_sentiment (those only exist for pipeline-tracked
    jobs). Backfilled entries still contribute raw retention/CTR data to
    _derive_insights, just not to the sentiment/topic breakdowns."""
    log = _load_published_log()
    known_ids = {e.get("youtube_video_id") for e in log}

    added = 0
    for v in channel_videos:
        if v["video_id"] not in known_ids:
            log.append({
                "job_id": f"backfilled_{v['video_id']}",
                "topic": "",
                "title": v["title"],
                "video_type": "unknown",
                "youtube_video_id": v["video_id"],
                "privacy_status": "public",
                "verdict_sentiment": None,
                "published_at": v["published_at"],
                "backfilled": True,
            })
            added += 1

    if added:
        with open(Config.PUBLISHED_LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)


def run_weekly_analysis():
    """Main entry point — called by the weekly analytics_review workflow.
    Backfills from the live channel first, so older/manually-published
    videos are always included, then analyzes everything."""
    data_api, analytics_api = _get_clients()

    backfill_from_channel(data_api, analytics_api)

    log = _load_published_log()
    recent = [e for e in log if e.get("youtube_video_id")]
    # analyze everything if the channel is still small; cap at the most
    # recent 50 once the channel has real volume, to keep this fast
    recent = sorted(recent, key=lambda e: e["published_at"])[-50:]

    enriched = []
    for entry in recent:
        metrics = _fetch_video_metrics(analytics_api, entry["youtube_video_id"])
        if metrics:
            enriched.append({**entry, **metrics})

    insights = _derive_insights(enriched)

    os.makedirs(Config.STATE_DIR, exist_ok=True)
    out_path = os.path.join(Config.STATE_DIR, "performance_insights.json")
    with open(out_path, "w") as f:
        json.dump(insights, f, indent=2)

    return insights


def load_insights() -> dict:
    """Used by pipeline_runner before script generation. Returns None if
    there isn't enough data yet — scripting.py simply won't get the field."""
    path = os.path.join(Config.STATE_DIR, "performance_insights.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return None
    if data.get("status") != "ok":
        return None
    return data


if __name__ == "__main__":
    result = run_weekly_analysis()
    print(json.dumps(result, indent=2))
