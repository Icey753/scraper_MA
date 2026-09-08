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
from csv_utils import load_existing_ids, append_rows

load_dotenv()

logging.basicConfig(
    filename="logs/youtube_scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)


class QuotaExceededError(Exception):
    """Kuota YouTube Data API harian abis - beda dari error search biasa
    (video privat/dihapus dll) karena SEMUA call berikutnya bakal gagal juga,
    jadi gak ada gunanya lanjut nyoba keyword lain di run ini."""

VIDEO_CSV = "output/youtube_videos.csv"
COMMENT_CSV = "output/youtube_comments.csv"

VIDEO_FIELDS = [
    "video_id", "title", "channel", "published_at", "published_year", "published_month",
    "keyword", "category", "dimension",
]
COMMENT_FIELDS = [
    "video_id",
    "comment_id",
    "author",
    "text",
    "like_count",
    "published_at",
    "published_year",
    "published_month",
    "reply_count",
    "video_title",
    "channel",
    "keyword",
    "category",
    "dimension",
    "mentions_website_experience",
]


def raw_search_cache_path(year=None):
    """Nama file cache mentah - per-tahun kalau --year dipake, default lama
    kalau enggak (mode scan 'N hari terakhir')."""
    return f"output/_raw_search_cache_{year}.json" if year else "output/_raw_search_cache.json"


def year_month_from_iso(iso_string):
    """Ekstrak (year, month) dari timestamp RFC3339 (mis. published_at)."""
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.year, dt.month


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


def search_videos(
    keyword,
    max_results=15,
    channel_id=None,
    category="institusional",
    dimension=None,
    published_after=None,
    published_before=None,
):
    """Search video by keyword, return list of video_id + metadata.
    Kalau channel_id diisi, search dibatasi ke channel itu doang.
    published_after/published_before (RFC3339) default ke DAYS_LOOKBACK
    terakhir kalau gak diisi (mode scan biasa) - diisi eksplisit pas
    dipanggil dari mode --year (slice satu tahun kalender)."""
    if published_after is None:
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
        if published_before:
            params["publishedBefore"] = published_before
        if channel_id:
            params["channelId"] = channel_id

        try:
            response = youtube.search().list(**params).execute()
        except HttpError as e:
            reason = ""
            if e.error_details:
                reason = e.error_details[0].get("reason", "")
            if e.resp.status == 429 or reason in ("quotaExceeded", "rateLimitExceeded"):
                raise QuotaExceededError(str(e)) from e
            logger.error(f"Search error for keyword '{keyword}': {e}")
            break

        for item in response.get("items", []):
            published_at = item["snippet"]["publishedAt"]
            published_year, published_month = year_month_from_iso(published_at)
            videos.append(
                {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "published_at": published_at,
                    "published_year": published_year,
                    "published_month": published_month,
                    "keyword": keyword,
                    "category": category,
                    "dimension": dimension,
                }
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    logger.info(
        f"Keyword '{keyword}' (channel_id={channel_id}, category={category}, dimension={dimension}): "
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
            published_at = top["publishedAt"]
            published_year, published_month = year_month_from_iso(published_at)
            comments.append(
                {
                    "video_id": video_id,
                    "comment_id": item["snippet"]["topLevelComment"]["id"],
                    "author": top["authorDisplayName"],
                    "text": comment_text,
                    "like_count": top["likeCount"],
                    "published_at": published_at,
                    "published_year": published_year,
                    "published_month": published_month,
                    "reply_count": item["snippet"]["totalReplyCount"],
                    "mentions_website_experience": mentions_website_experience(comment_text),
                }
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments


def year_date_bounds(year):
    """RFC3339 publishedAfter/publishedBefore buat satu tahun kalender penuh."""
    published_after = datetime(year, 1, 1, tzinfo=timezone.utc).isoformat()
    published_before = datetime(year + 1, 1, 1, tzinfo=timezone.utc).isoformat()
    return published_after, published_before


def load_raw_cache(cache_path):
    """Load cache mentah kumulatif per tahun kalau udah ada, biar keyword yang
    udah pernah di-search gak di-search ulang pas nambah keyword baru ke
    config.py (hemat kuota). Cache lama (dari sebelum ada 'searched_keywords')
    tetap kebaca - keyword lamanya bakal ke-search ulang sekali doang buat
    ngisi tracking-nya, abis itu ikut ke-skip juga."""
    if not os.path.exists(cache_path):
        return {"searched_keywords": [], "videos": []}
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "searched_keywords": data.get("searched_keywords", []),
        "videos": data.get("videos", []),
    }


def fetch_raw_videos(year=None):
    """Bagian MAHAL - manggil YouTube search API. Cuma dipanggil di mode normal,
    hasilnya di-cache per tahun biar bisa di-refilter tanpa API call lagi.
    Kalau year diisi, search dibatasi ke tahun kalender itu (mode longitudinal
    2020-2026); kalau enggak, fallback ke DAYS_LOOKBACK terakhir (mode scan biasa).

    Cache per tahun bersifat KUMULATIF dan nyimpen daftar keyword yang udah
    pernah di-search - jadi kalau config.py nambah keyword baru, run ulang
    buat tahun yang sama cuma kena biaya kuota buat keyword yang baru aja.
    Kalau kuota API harian abis di tengah jalan, proses berhenti rapi (gak
    nyoba semua sisa keyword satu-satu) dan otomatis lanjut dari keyword yang
    belum sempat di-search pas di-run lagi."""
    channel_ids = resolve_channel_ids(config.CHANNEL_HANDLES) if config.CHANNEL_HANDLES else []
    if config.CHANNEL_HANDLES and not channel_ids:
        logger.warning("CHANNEL_HANDLES diisi tapi gak ada yang berhasil di-resolve, search jalan tanpa restriction")

    published_after, published_before = year_date_bounds(year) if year else (None, None)

    cache_path = raw_search_cache_path(year)
    cache = load_raw_cache(cache_path)
    all_videos = cache["videos"]
    searched = set(cache["searched_keywords"])
    quota_exceeded = False

    # Pass 1: keyword institusional per dimensi reputasi, dibatasi ke kanal berita (kalau ada)
    for dimension, keywords in config.KEYWORDS.items():
        if quota_exceeded:
            break
        for keyword in keywords:
            if quota_exceeded:
                break
            if channel_ids:
                for cid in channel_ids:
                    search_key = f"{keyword}@{cid}"
                    if search_key in searched:
                        logger.info(f"Keyword '{keyword}' (channel {cid}): udah pernah di-search, skip")
                        continue
                    try:
                        videos = search_videos(
                            keyword,
                            max_results=config.MAX_VIDEOS_PER_KEYWORD,
                            channel_id=cid,
                            category="institusional",
                            dimension=dimension,
                            published_after=published_after,
                            published_before=published_before,
                        )
                    except QuotaExceededError:
                        quota_exceeded = True
                        break
                    all_videos.extend(videos)
                    searched.add(search_key)
                    time.sleep(0.3)
            else:
                if keyword in searched:
                    logger.info(f"Keyword '{keyword}': udah pernah di-search, skip (hemat kuota)")
                    continue
                try:
                    videos = search_videos(
                        keyword,
                        max_results=config.MAX_VIDEOS_PER_KEYWORD,
                        category="institusional",
                        dimension=dimension,
                        published_after=published_after,
                        published_before=published_before,
                    )
                except QuotaExceededError:
                    quota_exceeded = True
                    break
                all_videos.extend(videos)
                searched.add(keyword)
            time.sleep(0.5)

    # Pass 2: keyword tutorial/how-to soal website/aplikasi MA, LINTAS SEMUA KANAL
    # (gak dibatasi channel_ids - tutorial gini biasanya dari creator individu).
    # Selalu dimension="layanan_digital_ux" - video tutorial ini emang soal itu.
    if not quota_exceeded:
        for keyword in config.WEBSITE_KEYWORDS:
            if keyword in searched:
                logger.info(f"Keyword '{keyword}': udah pernah di-search, skip (hemat kuota)")
                continue
            try:
                videos = search_videos(
                    keyword,
                    max_results=config.MAX_VIDEOS_PER_KEYWORD,
                    category="tutorial_website",
                    dimension="layanan_digital_ux",
                    published_after=published_after,
                    published_before=published_before,
                )
            except QuotaExceededError:
                quota_exceeded = True
                break
            all_videos.extend(videos)
            searched.add(keyword)
            time.sleep(0.5)

    # Simpan mentah ke cache SEBELUM difilter, biar run --refilter berikutnya
    # bisa nge-tweak config.py (RELEVANCE_TERMS, EXCLUDE_TERMS, dll) tanpa
    # manggil search API lagi sama sekali (nol quota).
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "searched_keywords": sorted(searched),
                "videos": all_videos,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(f"Cache mentah disimpan: {len(all_videos)} video -> {cache_path}")

    if quota_exceeded:
        logger.warning(
            "Kuota YouTube API harian abis - run dihentikan di tengah jalan. "
            "Keyword yang belum sempat di-search bakal otomatis lanjut di run berikutnya."
        )
        print(
            "PERINGATAN: kuota YouTube API harian abis. Keyword yang udah sempat "
            "di-search udah aman ke-cache - tinggal run lagi nanti buat lanjutin "
            "sisanya, gak perlu ulang dari awal."
        )

    return all_videos


def load_cached_videos(year=None):
    """Bagian GRATIS - baca hasil search yang udah di-cache dari run sebelumnya.
    Dipake pas --refilter, buat ngetes perubahan config.py tanpa buang quota API."""
    cache_path = raw_search_cache_path(year)
    if not os.path.exists(cache_path):
        raise FileNotFoundError(
            f"{cache_path} belum ada - jalanin dulu 'python youtube_scraper.py"
            f"{f' --year {year}' if year else ''}' (mode normal, manggil API) "
            f"minimal sekali sebelum pake --refilter."
        )
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Load {len(data['videos'])} video dari cache (disimpan {data['cached_at']})")
    return data["videos"]


def run(use_cache=False, year=None):
    existing_video_ids = load_existing_ids(VIDEO_CSV, "video_id")
    logger.info(f"Video yang udah ada di {VIDEO_CSV}: {len(existing_video_ids)}")

    if use_cache:
        all_videos = load_cached_videos(year)
    else:
        all_videos = fetch_raw_videos(year)

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
            c["dimension"] = v["dimension"]
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
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Slice search ke satu tahun kalender (mis. 2022) buat tracking tren "
        "longitudinal. Tanpa ini, fallback ke mode scan DAYS_LOOKBACK hari terakhir. "
        "Quota search: ~1 call x 100 unit per keyword per tahun - jalanin satu tahun "
        "per hari kalau budget quota harian mepet.",
    )
    args = parser.parse_args()
    if args.year is not None and not (config.START_YEAR <= args.year <= config.END_YEAR):
        parser.error(f"--year harus di antara {config.START_YEAR}-{config.END_YEAR}")
    run(use_cache=args.refilter, year=args.year)