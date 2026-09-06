"""
Config terpusat: keyword list, target channel, dan parameter waktu.
Edit KEYWORDS dan CHANNEL_HANDLES sesuai isu yang lagi mau di-track.
"""

# Keyword pencarian - kombinasikan istilah umum + istilah spesifik isu terkini
KEYWORDS = [
    "putusan Mahkamah Agung",
    "vonis MA",
    "kasasi MA",
    "peninjauan kembali MA",
    "mafia peradilan",
    "kode etik hakim agung",
    "SIPP error",
    "e-court kendala",
    "aplikasi pengadilan bermasalah",
    "direktori putusan MA",
]

# Term wajib: video cuma disimpan kalau title-nya ngandung minimal SATU dari term ini
# (case-insensitive, substring match). Ini nyaring hasil "relevance fallback" YouTube
# yang suka nyempil (drama, DJ remix, dll) pas keyword pencarian terlalu spesifik/panjang
# dan gak ada video yang beneran match.
RELEVANCE_FILTER_TERMS = [
    "mahkamah agung",
    "mahkamah konstitusi",
    "pengadilan",
    "hakim",
    "putusan",
    "kasasi",
    "sipp",
    "e-court",
    "ecourt",
    "yudisial",
    "praperadilan",
    " ma ",  # spasi di kedua sisi biar gak nge-match kata "makan", "mana", dll
]

# (Opsional) batasi pencarian YouTube ke kanal berita tertentu biar hasil lebih representatif
# publik umum. Kosongkan list ini kalau mau search lintas semua kanal.
# CATATAN: kalau diisi, quota search terpakai per-channel (dikali jumlah channel),
# jadi kurangin MAX_VIDEOS_PER_KEYWORD kalau quota mepet.
CHANNEL_HANDLES = [
    "@KompasTV",
    "@CNNIndonesia",
    "@tvOneNews",
]

# Subreddit yang di-search (gabung pake "+" ala PRAW multi-sub search)
SUBREDDITS = "indonesia+hukum"

# Rentang waktu (dalam hari ke belakang dari hari ini) buat filter YouTube publishedAfter
DAYS_LOOKBACK = 180

# Reddit time_filter: hour, day, week, month, year, all
REDDIT_TIME_FILTER = "year"

# Batas jumlah video per keyword (jaga quota YouTube API - search = 100 unit/call)
MAX_VIDEOS_PER_KEYWORD = 15

# Batas jumlah post per keyword per subreddit (Reddit search)
MAX_POSTS_PER_KEYWORD = 50