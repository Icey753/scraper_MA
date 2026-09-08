"""
Helper CSV append + dedup, dipake bareng sama youtube_scraper.py dan
reddit_scraper.py biar dua-duanya nulis incremental (gak overwrite data lama)
dan gak nyimpen baris yang ID-nya udah pernah ke-scrap.
"""

import csv
import os


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
