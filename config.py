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
    "susah akses putusan MA",
    "website Mahkamah Agung",
    "direktori putusan MA",
]

# (Opsional) batasi pencarian YouTube ke kanal berita tertentu biar hasil lebih representatif publik umum.
# Kosongkan list ini kalau mau search lintas semua kanal.
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
