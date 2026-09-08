"""
Analisis sentimen buat komentar YouTube yang udah discrap.
Baca output/youtube_comments.csv, skor tiap komentar pake sentiment_lexicon,
keluarin:
- output/sentiment_detail.csv   -> tiap komentar + label sentimennya (buat spot-check)
- output/sentiment_summary.csv  -> agregat per keyword, per category, dan overall

Usage:
    python analyze_sentiment.py
"""

import csv
import logging

from sentiment_lexicon import score_sentiment

COMMENT_CSV = "output/youtube_comments.csv"
DETAIL_CSV = "output/sentiment_detail.csv"
SUMMARY_CSV = "output/sentiment_summary.csv"

DETAIL_FIELDS = ["comment_id", "video_id", "keyword", "category", "text", "sentiment"]
SUMMARY_FIELDS = [
    "group_type", "group_value", "total_comments",
    "positif", "netral", "negatif",
    "pct_positif", "pct_netral", "pct_negatif",
]

logging.basicConfig(
    filename="logs/analyze_sentiment.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def load_comments():
    with open(COMMENT_CSV, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def score_comments(comments):
    """Tambahin field 'sentiment' ke tiap dict komentar (in place), balikin daftarnya."""
    for c in comments:
        c["sentiment"] = score_sentiment(c["text"])
    return comments


def summarize_group(group_type, group_value, comments):
    total = len(comments)
    positif = sum(1 for c in comments if c["sentiment"] == "positif")
    netral = sum(1 for c in comments if c["sentiment"] == "netral")
    negatif = sum(1 for c in comments if c["sentiment"] == "negatif")
    return {
        "group_type": group_type,
        "group_value": group_value,
        "total_comments": total,
        "positif": positif,
        "netral": netral,
        "negatif": negatif,
        "pct_positif": round(100 * positif / total, 1) if total else 0,
        "pct_netral": round(100 * netral / total, 1) if total else 0,
        "pct_negatif": round(100 * negatif / total, 1) if total else 0,
    }


def build_summary(comments):
    rows = [summarize_group("overall", "all", comments)]

    keywords = sorted({c["keyword"] for c in comments})
    for kw in keywords:
        subset = [c for c in comments if c["keyword"] == kw]
        rows.append(summarize_group("keyword", kw, subset))

    categories = sorted({c["category"] for c in comments})
    for cat in categories:
        subset = [c for c in comments if c["category"] == cat]
        rows.append(summarize_group("category", cat, subset))

    return rows


def write_csv(filepath, rows, fieldnames):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run():
    comments = load_comments()
    logger.info(f"Load {len(comments)} komentar dari {COMMENT_CSV}")

    score_comments(comments)

    detail_rows = [{field: c[field] for field in DETAIL_FIELDS} for c in comments]
    write_csv(DETAIL_CSV, detail_rows, DETAIL_FIELDS)

    summary_rows = build_summary(comments)
    write_csv(SUMMARY_CSV, summary_rows, SUMMARY_FIELDS)

    overall = summary_rows[0]
    logger.info(
        f"Selesai. {overall['total_comments']} komentar: "
        f"{overall['positif']} positif, {overall['netral']} netral, {overall['negatif']} negatif"
    )
    print(
        f"Done: {overall['total_comments']} komentar dianalisis "
        f"({overall['pct_positif']}% positif, {overall['pct_netral']}% netral, {overall['pct_negatif']}% negatif) "
        f"-> {DETAIL_CSV} / {SUMMARY_CSV}"
    )


if __name__ == "__main__":
    run()
