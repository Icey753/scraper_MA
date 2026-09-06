"""
Reddit scraper:
- Search post berdasarkan keyword
- Tarik post + comments
- Filter comment yang relevan dengan Mahkamah Agung
- Simpan post dan comment yang lolos relevance filter

Pakai PRAW (API resmi Reddit).
"""

import os
import csv
import time
import logging
import re

import praw
from dotenv import load_dotenv

import config

load_dotenv()

logging.basicConfig(
    filename="logs/reddit_scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)


reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)


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

def search_posts(keyword, max_results=50):
    """
    Search post berdasarkan keyword di subreddit
    yang ditentukan di config.SUBREDDITS.
    """

    posts = []
    subreddit = reddit.subreddit(config.SUBREDDITS)

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

            posts.append(
                {
                    "post_id": submission.id,
                    "title": submission.title,
                    "subreddit": str(submission.subreddit),
                    "author": str(submission.author),
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "url": submission.url,
                    "selftext": submission.selftext[:2000],
                    "keyword": keyword,

                    # Apakah post-nya sendiri menyebut MA?
                    "post_ma_related": is_ma_related(post_text),
                }
            )

    except Exception as e:
        logger.error(
            f"Search error for keyword '{keyword}': {e}"
        )

    logger.info(
        f"Keyword '{keyword}': ditemukan {len(posts)} post"
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
        submission = reddit.submission(id=post_id)

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

            comments.append(
                {
                    "post_id": post_id,
                    "comment_id": c.id,
                    "author": str(c.author),
                    "text": comment_text,
                    "score": c.score,
                    "created_utc": c.created_utc,

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
# MAIN PIPELINE
# ============================================================

def run():

    all_posts = []
    all_comments = []

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    for keyword in config.KEYWORDS:

        posts = search_posts(
            keyword,
            max_results=config.MAX_POSTS_PER_KEYWORD,
        )

        all_posts.extend(posts)

        time.sleep(0.5)

    # --------------------------------------------------------
    # DEDUP POST
    # --------------------------------------------------------

    seen = set()
    unique_posts = []

    for p in all_posts:

        if p["post_id"] not in seen:

            seen.add(p["post_id"])
            unique_posts.append(p)

    logger.info(
        f"Total post unik: {len(unique_posts)}"
    )

    # --------------------------------------------------------
    # GET COMMENTS
    # --------------------------------------------------------

    for p in unique_posts:

        comments = get_comments(
            post_id=p["post_id"],
            post_title=p["title"],
            post_text=p["selftext"],
            max_comments=config.MAX_COMMENTS_PER_POST,
        )

        for c in comments:

            c["keyword"] = p["keyword"]
            c["subreddit"] = p["subreddit"]
            c["post_ma_related"] = p["post_ma_related"]

        all_comments.extend(comments)

        time.sleep(0.3)

    # --------------------------------------------------------
    # SAVE POSTS
    # --------------------------------------------------------

    os.makedirs("output", exist_ok=True)

    if unique_posts:

        with open(
            "output/reddit_posts.csv",
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=unique_posts[0].keys(),
            )

            writer.writeheader()
            writer.writerows(unique_posts)

    # --------------------------------------------------------
    # SAVE COMMENTS
    # --------------------------------------------------------

    if all_comments:

        with open(
            "output/reddit_comments.csv",
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=all_comments[0].keys(),
            )

            writer.writeheader()
            writer.writerows(all_comments)

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
        f"{len(unique_posts)} post, "
        f"{len(all_comments)} komentar relevan. "
        f"Direct={direct}, Contextual={contextual}"
    )

    print(
        f"Done: "
        f"{len(unique_posts)} post, "
        f"{len(all_comments)} komentar relevan "
        f"(direct={direct}, contextual={contextual})"
    )


if __name__ == "__main__":
    run()