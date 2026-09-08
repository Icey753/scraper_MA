"""
Ringkasan tren reputasi Mahkamah Agung per tahun, gabungan YouTube + Reddit.

Baca output/youtube_comments.csv dan output/reddit_comments.csv (skip yang
belum ada - misal Reddit belum pernah berhasil discrap), skor tiap baris pake
sentiment_lexicon, lalu agregasi per (tahun, dimension, source) jadi satu CSV.

Dimension (integritas_korupsi / putusan_kontroversial / layanan_digital_ux)
dipake sebagai pengganti topic modeling: komentar publik di YouTube/Reddit
terlalu pendek & noisy (banyak nyasar ke topik gak berhubungan) buat
unsupervised topic modeling yang koheren, jadi tren "topik" di sini nempel ke
keyword yang emang sengaja dicari - bukan hasil clustering otomatis.

Usage:
    python analyze_reputation.py
"""

import csv
import logging
import os

from sentiment_lexicon import score_sentiment

SOURCES = [
    {"name": "youtube", "path": "output/youtube_comments.csv", "year_field": "published_year"},
    {"name": "reddit", "path": "output/reddit_comments.csv", "year_field": "created_year"},
]

SUMMARY_CSV = "output/reputation_trend.csv"
SUMMARY_FIELDS = [
    "year", "source", "dimension", "total_comments",
    "positif", "netral", "negatif",
    "pct_positif", "pct_netral", "pct_negatif",
]

logging.basicConfig(
    filename="logs/analyze_reputation.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def load_rows(source):
    """Baca satu source CSV, balikin list of dict ternormalisasi (year, source,
    dimension, sentiment). Balikin [] kalau file belum ada (belum pernah discrap)."""
    if not os.path.exists(source["path"]):
        logger.warning(f"{source['path']} belum ada, di-skip")
        return []

    rows = []
    with open(source["path"], "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            year_raw = row.get(source["year_field"])
            if not year_raw:
                continue
            rows.append(
                {
                    "year": int(year_raw),
                    "source": source["name"],
                    "dimension": row.get("dimension") or "tidak_ada_dimension",
                    "sentiment": score_sentiment(row.get("text", "")),
                }
            )
    logger.info(f"Load {len(rows)} baris dari {source['path']}")
    return rows


def summarize_group(year, source, dimension, rows):
    total = len(rows)
    positif = sum(1 for r in rows if r["sentiment"] == "positif")
    netral = sum(1 for r in rows if r["sentiment"] == "netral")
    negatif = sum(1 for r in rows if r["sentiment"] == "negatif")
    return {
        "year": year,
        "source": source,
        "dimension": dimension,
        "total_comments": total,
        "positif": positif,
        "netral": netral,
        "negatif": negatif,
        "pct_positif": round(100 * positif / total, 1) if total else 0,
        "pct_netral": round(100 * netral / total, 1) if total else 0,
        "pct_negatif": round(100 * negatif / total, 1) if total else 0,
    }


def build_summary(all_rows):
    keys = sorted({(r["year"], r["source"], r["dimension"]) for r in all_rows})
    return [
        summarize_group(year, source, dimension, [
            r for r in all_rows
            if r["year"] == year and r["source"] == source and r["dimension"] == dimension
        ])
        for year, source, dimension in keys
    ]


def run():
    all_rows = []
    for source in SOURCES:
        all_rows.extend(load_rows(source))

    if not all_rows:
        print("Gak ada data buat dianalisis - jalanin scraper dulu.")
        return

    summary_rows = build_summary(all_rows)

    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)

    years_covered = sorted({r["year"] for r in all_rows})
    logger.info(f"Selesai. {len(all_rows)} baris, {len(summary_rows)} baris ringkasan, tahun: {years_covered}")
    print(
        f"Done: {len(all_rows)} komentar dianalisis, tahun tercakup {years_covered} "
        f"-> {SUMMARY_CSV}"
    )


if __name__ == "__main__":
    run()
