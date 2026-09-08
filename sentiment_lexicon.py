"""
Lexicon sentimen sederhana buat komentar publik seputar Mahkamah Agung.
Scoped ke dua domain: trust institusional (korupsi, keadilan, dst) dan
pengalaman pakai website/aplikasi MA (error, lemot, dst) - domain kedua ini
sengaja overlap sama config.COMMENT_EXPERIENCE_TERMS karena keluhan teknis
website ITU SENDIRI adalah sinyal sentimen negatif buat konteks redesign.

Cara kerja: hitung berapa term positif vs negatif yang match di teks (regex,
biar "korupsi" gak ke-match di tengah kata lain), net score-nya nentuin label.
"""

import re

POSITIVE_TERMS = [
    "bagus", "mantap", "keren", "membantu", "memudahkan", "mudah",
    "praktis", "transparan", "profesional", "terpercaya",
    "puas", "memuaskan", "gampang", "berhasil", "sukses", "apresiasi",
    "terima kasih", "makasih", "solutif", "responsif", "ramah",
]

NEGATIVE_TERMS = [
    "buruk", "jelek", "kecewa", "mengecewakan", "payah", "parah",
    "lambat", "lemot", "ribet", "susah", "sulit", "error", "eror",
    "gagal", "rusak", "bohong", "curang", "tidak becus", "memalukan",
    "memprihatinkan", "korupsi", "suap", "mafia", "zalim", "culas",
    "tidak adil", "gak adil", "gak bisa dibuka", "ga bisa dibuka",
    "tidak bisa diakses", "susah diakses", "down", "maintenance",
    "gagal login", "gagal upload",
]

_POSITIVE_PATTERNS = [re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE) for term in POSITIVE_TERMS]
_NEGATIVE_PATTERNS = [re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE) for term in NEGATIVE_TERMS]


def score_sentiment(text):
    """Hitung net skor sentimen (positif_hits - negatif_hits), balikin label
    'positif' / 'netral' / 'negatif'. Netral kalau skor 0 (termasuk kalau
    gak ada term yang match sama sekali)."""
    if not text:
        return "netral"

    positive_hits = sum(1 for pattern in _POSITIVE_PATTERNS if pattern.search(text))
    negative_hits = sum(1 for pattern in _NEGATIVE_PATTERNS if pattern.search(text))
    net = positive_hits - negative_hits

    if net > 0:
        return "positif"
    if net < 0:
        return "negatif"
    return "netral"
