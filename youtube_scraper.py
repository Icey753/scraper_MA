"""
YouTube scraper: search video berdasarkan keyword, lalu tarik comment threads.
Pake YouTube Data API v3 resmi (gratis, quota 10.000 unit/hari default).

Quota cost:
- search().list()          = 100 unit per call
- commentThreads().list()  = 1 unit per call (per page, max 100 comment/page)
"""

import os
import csv
import time
import logging
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

load_dotenv()

logging.basicConfig(
    filename="logs/youtube_scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)


def search_videos(keyword, max_results=15):
    """Search video by keyword, return list of video_id + metadata."""
    published_after = (
        datetime.now(timezone.utc) - timedelta(days=config.DAYS_LOOKBACK)
    ).isoformat()

    videos = []
    next_page_token = None

    while len(videos) < max_results:
        try:
            request = youtube.search().list(
                q=keyword,
                part="id,snippet",
                type="video",
                order="relevance",
                publishedAfter=published_after,
                relevanceLanguage="id",
                maxResults=min(50, max_results - len(videos)),
                pageToken=next_page_token,
            )
            response = request.execute()
        except HttpError as e:
            logger.error(f"Search error for keyword '{keyword}': {e}")
            break

        for item in response.get("items", []):
            videos.append(
                {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "published_at": item["snippet"]["publishedAt"],
                    "keyword": keyword,
                }
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    logger.info(f"Keyword '{keyword}': ditemukan {len(videos)} video")
    return videos


def get_comments(video_id, max_comments=200):
    """Tarik top-level comments + reply count dari satu video."""
    comments = []
    next_page_token = None

    while len(comments) < max_comments:
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                order="relevance",
                pageToken=next_page_token,
                textFormat="plainText",
            )
            response = request.execute()
        except HttpError as e:
            # Comment disabled atau video private/deleted - skip aja
            logger.warning(f"Gagal ambil komentar video {video_id}: {e}")
            break

        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            comments.append(
                {
                    "video_id": video_id,
                    "comment_id": item["snippet"]["topLevelComment"]["id"],
                    "author": top["authorDisplayName"],
                    "text": top["textDisplay"],
                    "like_count": top["likeCount"],
                    "published_at": top["publishedAt"],
                    "reply_count": item["snippet"]["totalReplyCount"],
                }
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments


def run():
    all_videos = []
    all_comments = []

    for keyword in config.KEYWORDS:
        videos = search_videos(keyword, max_results=config.MAX_VIDEOS_PER_KEYWORD)
        all_videos.extend(videos)
        time.sleep(0.5)  # jaga-jaga rate limit

    # Dedup video by video_id (bisa muncul di lebih dari satu keyword)
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            unique_videos.append(v)

    logger.info(f"Total video unik: {len(unique_videos)}")

    for v in unique_videos:
        comments = get_comments(v["video_id"])
        for c in comments:
            c["video_title"] = v["title"]
            c["channel"] = v["channel"]
            c["keyword"] = v["keyword"]
        all_comments.extend(comments)
        time.sleep(0.3)

    # Simpan ke CSV
    with open("output/youtube_videos.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=unique_videos[0].keys() if unique_videos else [])
        writer.writeheader()
        writer.writerows(unique_videos)

    if all_comments:
        with open("output/youtube_comments.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_comments[0].keys())
            writer.writeheader()
            writer.writerows(all_comments)

    logger.info(f"Selesai. {len(unique_videos)} video, {len(all_comments)} komentar disimpan.")
    print(f"Done: {len(unique_videos)} video, {len(all_comments)} komentar -> output/")


if __name__ == "__main__":
    run()
