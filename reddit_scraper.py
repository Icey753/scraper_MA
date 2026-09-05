"""
Reddit scraper: search post berdasarkan keyword lintas subreddit, tarik post + top comments.
Pake PRAW (API resmi Reddit, gratis buat non-commercial use).
"""

import os
import csv
import time
import logging

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


def search_posts(keyword, max_results=50):
    """Search post by keyword di subreddit yang ditentukan di config.SUBREDDITS."""
    posts = []
    subreddit = reddit.subreddit(config.SUBREDDITS)

    try:
        for submission in subreddit.search(
            keyword,
            sort="new",
            time_filter=config.REDDIT_TIME_FILTER,
            limit=max_results,
        ):
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
                    "selftext": submission.selftext[:1000],  # potong biar CSV gak bengkak
                    "keyword": keyword,
                }
            )
    except Exception as e:
        logger.error(f"Search error for keyword '{keyword}': {e}")

    logger.info(f"Keyword '{keyword}': ditemukan {len(posts)} post")
    return posts


def get_comments(post_id, max_comments=100):
    """Tarik komentar dari satu post (flatten, skip 'load more' nodes)."""
    comments = []
    try:
        submission = reddit.submission(id=post_id)
        submission.comments.replace_more(limit=0)  # buang "load more comments" node
        for c in submission.comments.list()[:max_comments]:
            comments.append(
                {
                    "post_id": post_id,
                    "comment_id": c.id,
                    "author": str(c.author),
                    "text": c.body,
                    "score": c.score,
                    "created_utc": c.created_utc,
                }
            )
    except Exception as e:
        logger.warning(f"Gagal ambil komentar post {post_id}: {e}")

    return comments


def run():
    all_posts = []
    all_comments = []

    for keyword in config.KEYWORDS:
        posts = search_posts(keyword, max_results=config.MAX_POSTS_PER_KEYWORD)
        all_posts.extend(posts)
        time.sleep(0.5)

    # Dedup post by post_id
    seen = set()
    unique_posts = []
    for p in all_posts:
        if p["post_id"] not in seen:
            seen.add(p["post_id"])
            unique_posts.append(p)

    logger.info(f"Total post unik: {len(unique_posts)}")

    for p in unique_posts:
        comments = get_comments(p["post_id"])
        for c in comments:
            c["keyword"] = p["keyword"]
            c["post_title"] = p["title"]
        all_comments.extend(comments)
        time.sleep(0.3)

    with open("output/reddit_posts.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=unique_posts[0].keys() if unique_posts else [])
        writer.writeheader()
        writer.writerows(unique_posts)

    if all_comments:
        with open("output/reddit_comments.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_comments[0].keys())
            writer.writeheader()
            writer.writerows(all_comments)

    logger.info(f"Selesai. {len(unique_posts)} post, {len(all_comments)} komentar disimpan.")
    print(f"Done: {len(unique_posts)} post, {len(all_comments)} komentar -> output/")


if __name__ == "__main__":
    run()
