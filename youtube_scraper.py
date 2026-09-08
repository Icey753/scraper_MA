"""
YouTube scraper: search video berdasarkan keyword, lalu tarik comment threads.
Pake YouTube Data API v3 resmi (gratis, quota 10.000 unit/hari default).

Quota cost:
- search().list()          = 100 unit per call
- commentThreads().list()  = 1 unit per call (per page, max 100 comment/page)
"""

import os
import re
import csv
import json
import time
import logging
import argparse
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

VIDEO_CSV = "output/youtube_videos.csv"
COMMENT_CSV = "output/youtube_comments.csv"
RAW_SEARCH_CACHE = "output/_raw_search_cache.json"

VIDEO_FIELDS = ["video_id", "title", "channel", "published_at", "keyword", "category"]
COMMENT_FIELDS = [
    "video_id",
    "comment_id",
    "author",
    "text",
    "like_count",
    "published_at",
    "reply_count",
    "video_title",
    "channel",
    "keyword",
    "category",
    "mentions_website_experience",
]


def load_existing_ids(filepath, id_field):
    """Baca CSV lama (kalau ada), balikin set of id yang udah pernah discrap."""
    ids = set()
    if os.path.exists(filepath):
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.add(row[id_field])
    return ids


def append_rows(filepath, rows, fieldnames):
    """Tambahin baris baru ke CSV. Nulis header cuma kalau file belum ada."""
    if not rows:
        return
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def mentions_ma_abbreviation(text):
    """Deteksi abbreviation 'MA' pake word boundary regex, biar tetep kedeteksi
    walau nempel tanda baca (mis. 'Putusan MA,' atau '"MA" resmi')."""
    return bool(re.search(r"\bma\b", text, re.IGNORECASE))


def is_relevant(title, category="institusional"):
    """True kalau title ngandung minimal satu term wajib buat kategori terkait.
    Institusional dan tutorial_website punya term list beda - tutorial jarang
    nyebut 'Mahkamah Agung' eksplisit walau isinya tentang sistem MA (e-Court/SIPP)."""
    text = title.lower()
    if mentions_ma_abbreviation(title):
        return True
    terms = (
        config.WEBSITE_RELEVANCE_TERMS
        if category == "tutorial_website"
        else config.INSTITUTIONAL_RELEVANCE_TERMS
    )
    return any(term.lower() in text for term in terms if term.strip() != "ma")


def is_excluded(title, channel=""):
    """True kalau title ATAU nama channel kena EXCLUDE_TERMS (misal konten/kanal
    Mahkamah Konstitusi) dan gak nyebut Mahkamah Agung secara eksplisit di title."""
    text = f" {title.lower()} {channel.lower()} "
    mentions_exclude = any(term.lower() in text for term in config.EXCLUDE_TERMS)
    mentions_ma = ("mahkamah agung" in text) or mentions_ma_abbreviation(title)
    return mentions_exclude and not mentions_ma


def mentions_website_experience(text):
    """True kalau komentar ngandung istilah yang nunjukin pengalaman pakai
    website/aplikasi (error, lemot, susah diakses, dst) - bukan cuma bahas kasus hukum."""
    text_lower = text.lower()
    return any(term in text_lower for term in config.COMMENT_EXPERIENCE_TERMS)


def resolve_channel_ids(handles):
    """Convert @handle jadi channel_id (dibutuhin buat filter search per channel)."""
    ids = []
    for handle in handles:
        h = handle.lstrip("@")
        try:
            response = youtube.channels().list(part="id", forHandle=h).execute()
            items = response.get("items", [])
            if items:
                ids.append(items[0]["id"])
            else:
                logger.warning(f"Handle @{h} gak ketemu channel_id-nya, di-skip")
        except HttpError as e:
            logger.warning(f"Gagal resolve channel @{h}: {e}")
    return ids


def search_videos(keyword, max_results=15, channel_id=None, category="institusional"):
    """Search video by keyword, return list of video_id + metadata.
    Kalau channel_id diisi, search dibatasi ke channel itu doang."""
    published_after = (
        datetime.now(timezone.utc) - timedelta(days=config.DAYS_LOOKBACK)
    ).isoformat()

    videos = []
    next_page_token = None

    while len(videos) < max_results:
        params = dict(
            q=keyword,
            part="id,snippet",
            type="video",
            order="relevance",
            publishedAfter=published_after,
            relevanceLanguage="id",
            maxResults=min(50, max_results - len(videos)),
            pageToken=next_page_token,
        )
        if channel_id:
            params["channelId"] = channel_id

        try:
            response = youtube.search().list(**params).execute()
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
                    "category": category,
                }
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    logger.info(
        f"Keyword '{keyword}' (channel_id={channel_id}, category={category}): "
        f"ditemukan {len(videos)} video mentah"
    )
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
            comment_text = top["textDisplay"]
            comments.append(
                {
                    "video_id": video_id,
                    "comment_id": item["snippet"]["topLevelComment"]["id"],
                    "author": top["authorDisplayName"],
                    "text": comment_text,
                    "like_count": top["likeCount"],
                    "published_at": top["publishedAt"],
                    "reply_count": item["snippet"]["totalReplyCount"],
                    "mentions_website_experience": mentions_website_experience(comment_text),
                }
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments


def fetch_raw_videos():
    """Bagian MAHAL - manggil YouTube search API. Cuma dipanggil di mode normal,
    hasilnya di-cache ke RAW_SEARCH_CACHE biar bisa di-refilter tanpa API call lagi."""
    channel_ids = resolve_channel_ids(config.CHANNEL_HANDLES) if config.CHANNEL_HANDLES else []
    if config.CHANNEL_HANDLES and not channel_ids:
        logger.warning("CHANNEL_HANDLES diisi tapi gak ada yang berhasil di-resolve, search jalan tanpa restriction")

    all_videos = []

    # Pass 1: keyword institusional, dibatasi ke kanal berita (kalau ada)
    for keyword in config.KEYWORDS:
        if channel_ids:
            for cid in channel_ids:
                videos = search_videos(
                    keyword, max_results=config.MAX_VIDEOS_PER_KEYWORD, channel_id=cid, category="institusional"
                )
                all_videos.extend(videos)
                time.sleep(0.3)
        else:
            videos = search_videos(keyword, max_results=config.MAX_VIDEOS_PER_KEYWORD, category="institusional")
            all_videos.extend(videos)
        time.sleep(0.5)

    # Pass 2: keyword tutorial/how-to soal website/aplikasi MA, LINTAS SEMUA KANAL
    # (gak dibatasi channel_ids - tutorial gini biasanya dari creator individu)
    for keyword in config.WEBSITE_KEYWORDS:
        videos = search_videos(keyword, max_results=config.MAX_VIDEOS_PER_KEYWORD, category="tutorial_website")
        all_videos.extend(videos)
        time.sleep(0.5)

    # Simpan mentah ke cache SEBELUM difilter, biar run --refilter berikutnya
    # bisa nge-tweak config.py (RELEVANCE_TERMS, EXCLUDE_TERMS, dll) tanpa
    # manggil search API lagi sama sekali (nol quota).
    with open(RAW_SEARCH_CACHE, "w", encoding="utf-8") as f:
        json.dump(
            {"cached_at": datetime.now(timezone.utc).isoformat(), "videos": all_videos},
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(f"Cache mentah disimpan: {len(all_videos)} video -> {RAW_SEARCH_CACHE}")

    return all_videos


def load_cached_videos():
    """Bagian GRATIS - baca hasil search yang udah di-cache dari run sebelumnya.
    Dipake pas --refilter, buat ngetes perubahan config.py tanpa buang quota API."""
    if not os.path.exists(RAW_SEARCH_CACHE):
        raise FileNotFoundError(
            f"{RAW_SEARCH_CACHE} belum ada - jalanin dulu 'python youtube_scraper.py' "
            f"(mode normal, manggil API) minimal sekali sebelum pake --refilter."
        )
    with open(RAW_SEARCH_CACHE, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Load {len(data['videos'])} video dari cache (disimpan {data['cached_at']})")
    return data["videos"]


def run(use_cache=False):
    existing_video_ids = load_existing_ids(VIDEO_CSV, "video_id")
    logger.info(f"Video yang udah ada di {VIDEO_CSV}: {len(existing_video_ids)}")

    if use_cache:
        all_videos = load_cached_videos()
    else:
        all_videos = fetch_raw_videos()

    # Dedup video by video_id (bisa muncul di lebih dari satu keyword/channel dalam run yang sama)
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            unique_videos.append(v)

    # Buang video yang title-nya gak ngandung term wajib apapun (nyaring hasil
    # "relevance fallback" YouTube yang ngasal - drama, DJ remix, dll)
    before_filter = len(unique_videos)
    unique_videos = [v for v in unique_videos if is_relevant(v["title"], v["category"])]
    dropped_irrelevant = before_filter - len(unique_videos)

    # Buang video yang keknya soal Mahkamah Konstitusi (MK), bukan Mahkamah Agung (MA)
    before_exclude = len(unique_videos)
    unique_videos = [v for v in unique_videos if not is_excluded(v["title"], v["channel"])]
    dropped_mk = before_exclude - len(unique_videos)

    # Skip video yang udah pernah discrap di run sebelumnya
    new_videos = [v for v in unique_videos if v["video_id"] not in existing_video_ids]
    skipped = len(unique_videos) - len(new_videos)
    logger.info(
        f"Hasil {'cache' if use_cache else 'search'}: {before_filter} video unik mentah, "
        f"{dropped_irrelevant} dibuang (gak relevan), "
        f"{dropped_mk} dibuang (konten MK bukan MA), "
        f"{skipped} udah pernah discrap (skip), {len(new_videos)} baru"
    )

    total_comments = 0
    total_experience_comments = 0
    for v in new_videos:
        comments = get_comments(v["video_id"])
        for c in comments:
            c["video_title"] = v["title"]
            c["channel"] = v["channel"]
            c["keyword"] = v["keyword"]
            c["category"] = v["category"]
            if c["mentions_website_experience"]:
                total_experience_comments += 1

        # Tulis langsung per-video (append), biar kalau script keputus di tengah
        # jalan, data yang udah kepegang gak ilang dan run berikutnya gak scrap ulang.
        append_rows(VIDEO_CSV, [v], VIDEO_FIELDS)
        append_rows(COMMENT_CSV, comments, COMMENT_FIELDS)

        total_comments += len(comments)
        time.sleep(0.3)

    logger.info(
        f"Selesai. {len(new_videos)} video baru, {total_comments} komentar baru "
        f"({total_experience_comments} nyebut pengalaman website)."
    )
    print(
        f"Done ({'refilter dari cache, 0 quota API' if use_cache else 'search API'}): "
        f"{len(new_videos)} video baru ditambahkan "
        f"({dropped_irrelevant} dibuang gak relevan, {dropped_mk} dibuang konten MK, {skipped} video lama di-skip), "
        f"{total_comments} komentar baru ({total_experience_comments} nyebut pengalaman website) "
        f"-> {VIDEO_CSV} / {COMMENT_CSV}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refilter",
        action="store_true",
        help="Pake hasil search yang udah di-cache, gak manggil API sama sekali (0 quota). "
        "Buat testing perubahan RELEVANCE_TERMS/EXCLUDE_TERMS di config.py.",
    )
    args = parser.parse_args()
    run(use_cache=args.refilter)