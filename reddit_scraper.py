"""
Reddit scraper:
- Search post berdasarkan keyword
- Tarik post + comments
- Filter comment yang relevan dengan Mahkamah Agung
- Simpan post dan comment yang lolos relevance filter

Pakai PRAW (API resmi Reddit).
"""

import os
import time
import logging
import re
from datetime import datetime, timezone

import praw
from dotenv import load_dotenv

import config
from csv_utils import load_existing_ids, append_rows

load_dotenv()

logging.basicConfig(
    filename="logs/reddit_scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)


_reddit = None


def get_reddit():
    """Bikin koneksi PRAW cuma pas beneran dipakai, bukan pas modul di-import -
    biar `python main.py --yt` gak ikut crash gara-gara credential Reddit belum ada."""
    global _reddit
    if _reddit is None:
        _reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )
    return _reddit


# ============================================================
# MA RELEVANCE
# ============================================================

MA_PATTERNS = [
    # Nama institusi
    r"\bmahkamah agung\b",
    r"\bmahkamah agung ri\b",
    r"\bmahkamah agung republik indonesia\b",

    # Singkatan
    r"\bMA\b",

    # Jabatan / aktor
    r"\bhakim agung\b",
    r"\bketua MA\b",
    r"\bwakil ketua MA\b",

    # Proses hukum yang sangat terkait MA
    r"\bputusan MA\b",
    r"\bkasasi\b",
    r"\bpeninjauan kembali\b",
    r"\bputusan kasasi\b",
    r"\bputusan peninjauan kembali\b",

    # Direktori / website MA
    r"\bputusan3\.mahkamahagung\.go\.id\b",
    r"\bdirektori putusan\b",
    r"\bwebsite MA\b",
    r"\bsitus MA\b",
    r"\bmahkamahagung\.go\.id\b",
]


def is_ma_related(text):
    """
    Cek apakah teks memiliki indikasi relevan dengan
    Mahkamah Agung.

    Return:
        True / False
    """

    if not text:
        return False

    text_lower = text.lower()

    for pattern in MA_PATTERNS:
        if re.search(pattern, text_lower, flags=re.IGNORECASE):
            return True

    return False


# ============================================================
# SEARCH POSTS
# ============================================================

def year_month_from_utc(created_utc):
    """Ekstrak (year, month) dari epoch timestamp created_utc Reddit."""
    dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
    return dt.year, dt.month


def search_posts(keyword, max_results=50, dimension=None):
    """
    Search post berdasarkan keyword di subreddit yang ditentukan di
    config.SUBREDDITS.

    CATATAN keterbatasan: Reddit API gak punya date-range search resmi
    (cloudsearch timestamp: syntax udah deprecated). sort="new" + time_filter
    dari config cuma ngasih submission terbaru yang match, jadi tahun-tahun
    lama (2020-2022) kemungkinan besar bakal tipis/kosong cakupannya - Reddit
    di sini best-effort/pelengkap, YouTube tetap sumber utama buat tren tahunan.
    """

    posts = []
    subreddit = get_reddit().subreddit(config.SUBREDDITS)

    try:
        for submission in subreddit.search(
            keyword,
            sort="new",
            time_filter=config.REDDIT_TIME_FILTER,
            limit=max_results,
        ):

            post_text = (
                submission.title
                + " "
                + submission.selftext
            )

            created_year, created_month = year_month_from_utc(submission.created_utc)

            posts.append(
                {
                    "post_id": submission.id,
                    "title": submission.title,
                    "subreddit": str(submission.subreddit),
                    "author": str(submission.author),
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "created_year": created_year,
                    "created_month": created_month,
                    "url": submission.url,
                    "selftext": submission.selftext[:2000],
                    "keyword": keyword,
                    "dimension": dimension,

                    # Apakah post-nya sendiri menyebut MA?
                    "post_ma_related": is_ma_related(post_text),
                }
            )

    except Exception as e:
        logger.error(
            f"Search error for keyword '{keyword}': {e}"
        )

    logger.info(
        f"Keyword '{keyword}' (dimension={dimension}): ditemukan {len(posts)} post"
    )

    return posts


# ============================================================
# COMMENTS
# ============================================================

def get_comments(
    post_id,
    post_title="",
    post_text="",
    max_comments=200,
):
    """
    Ambil komentar dari post.

    Hanya menyimpan komentar yang:
    1. menyebut MA secara langsung, ATAU
    2. berada pada post yang secara jelas membahas MA.
    """

    comments = []

    try:
        submission = get_reddit().submission(id=post_id)

        submission.comments.replace_more(limit=0)

        post_context = (
            post_title
            + " "
            + post_text
        )

        post_is_ma_related = is_ma_related(post_context)

        for c in submission.comments.list()[:max_comments]:

            if not c.body:
                continue

            comment_text = c.body

            # ------------------------------------------------
            # Relevance
            # ------------------------------------------------

            comment_directly_mentions_ma = is_ma_related(
                comment_text
            )

            # ------------------------------------------------
            # Strategy:
            #
            # A. comment menyebut MA -> lolos
            #
            # B. post membahas MA dan comment merupakan
            #    komentar pendek/kontekstual -> lolos
            #
            # C. post bukan tentang MA dan comment tidak
            #    menyebut MA -> buang
            # ------------------------------------------------

            if comment_directly_mentions_ma:
                relevance = "direct"

            elif post_is_ma_related:
                relevance = "contextual"

            else:
                continue

            created_year, created_month = year_month_from_utc(c.created_utc)

            comments.append(
                {
                    "post_id": post_id,
                    "comment_id": c.id,
                    "author": str(c.author),
                    "text": comment_text,
                    "score": c.score,
                    "created_utc": c.created_utc,
                    "created_year": created_year,
                    "created_month": created_month,

                    "relevance": relevance,
                    "ma_keyword": True,

                    "post_title": post_title,
                }
            )

    except Exception as e:
        logger.warning(
            f"Gagal ambil komentar post {post_id}: {e}"
        )

    return comments


# ============================================================
# CSV SCHEMA
# ============================================================

POST_CSV = "output/reddit_posts.csv"
COMMENT_CSV = "output/reddit_comments.csv"

POST_FIELDS = [
    "post_id", "title", "subreddit", "author", "score", "num_comments",
    "created_utc", "created_year", "created_month", "url", "selftext",
    "keyword", "dimension", "post_ma_related",
]
COMMENT_FIELDS = [
    "post_id", "comment_id", "author", "text", "score",
    "created_utc", "created_year", "created_month",
    "relevance", "ma_keyword", "post_title",
    "keyword", "subreddit", "dimension", "post_ma_related",
]


def in_tracked_range(created_year):
    return config.START_YEAR <= created_year <= config.END_YEAR


# ============================================================
# MAIN PIPELINE
# ============================================================

def run():

    os.makedirs("output", exist_ok=True)

    existing_post_ids = load_existing_ids(POST_CSV, "post_id")
    logger.info(f"Post yang udah ada di {POST_CSV}: {len(existing_post_ids)}")

    all_posts = []

    # --------------------------------------------------------
    # SEARCH (per dimensi reputasi, sama kayak youtube_scraper)
    # --------------------------------------------------------

    for dimension, keywords in config.KEYWORDS.items():

        for keyword in keywords:

            posts = search_posts(
                keyword,
                max_results=config.MAX_POSTS_PER_KEYWORD,
                dimension=dimension,
            )

            all_posts.extend(posts)

            time.sleep(0.5)

    # --------------------------------------------------------
    # DEDUP POST + FILTER RENTANG TAHUN
    # --------------------------------------------------------

    seen = set()
    unique_posts = []

    for p in all_posts:

        if p["post_id"] in seen:
            continue
        if not in_tracked_range(p["created_year"]):
            continue

        seen.add(p["post_id"])
        unique_posts.append(p)

    # Post yang belum pernah discrap di run sebelumnya
    new_posts = [p for p in unique_posts if p["post_id"] not in existing_post_ids]
    skipped = len(unique_posts) - len(new_posts)

    logger.info(
        f"Total post unik dalam rentang {config.START_YEAR}-{config.END_YEAR}: "
        f"{len(unique_posts)}, {skipped} udah pernah discrap (skip), {len(new_posts)} baru"
    )

    # --------------------------------------------------------
    # GET COMMENTS (cuma buat post baru)
    # --------------------------------------------------------

    all_comments = []

    for p in new_posts:

        comments = get_comments(
            post_id=p["post_id"],
            post_title=p["title"],
            post_text=p["selftext"],
            max_comments=config.MAX_COMMENTS_PER_POST,
        )

        for c in comments:

            c["keyword"] = p["keyword"]
            c["subreddit"] = p["subreddit"]
            c["dimension"] = p["dimension"]
            c["post_ma_related"] = p["post_ma_related"]

        comments = [c for c in comments if in_tracked_range(c["created_year"])]

        all_comments.extend(comments)

        # Tulis langsung per-post (append), sama pola kayak youtube_scraper -
        # data gak ilang kalau script keputus di tengah jalan.
        append_rows(POST_CSV, [p], POST_FIELDS)
        append_rows(COMMENT_CSV, comments, COMMENT_FIELDS)

        time.sleep(0.3)

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    direct = sum(
        1
        for c in all_comments
        if c["relevance"] == "direct"
    )

    contextual = sum(
        1
        for c in all_comments
        if c["relevance"] == "contextual"
    )

    logger.info(
        f"Selesai. "
        f"{len(new_posts)} post baru, "
        f"{len(all_comments)} komentar relevan baru. "
        f"Direct={direct}, Contextual={contextual}"
    )

    print(
        f"Done: "
        f"{len(new_posts)} post baru ({skipped} lama di-skip), "
        f"{len(all_comments)} komentar relevan baru "
        f"(direct={direct}, contextual={contextual}) "
        f"-> {POST_CSV} / {COMMENT_CSV}"
    )


if __name__ == "__main__":
    run()