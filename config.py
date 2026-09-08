"""
Config terpusat: keyword list, target channel, dan parameter waktu.
Edit KEYWORDS dan CHANNEL_HANDLES sesuai isu yang lagi mau di-track.
"""

# Keyword institusional - isu hukum & reputasi MA secara umum. Dibatasi ke kanal
# berita (lihat CHANNEL_HANDLES) biar hasilnya representatif publik umum.
KEYWORDS = [
    "putusan Mahkamah Agung",
    "vonis MA",
    "kasasi MA",
    "peninjauan kembali MA",
    "mafia peradilan",
    "kode etik hakim agung",
    "direktori putusan MA",
]

# Keyword tutorial/how-to - buat mancing komentar yang isinya PENGALAMAN NYATA pakai
# website/aplikasi MA. Orang jarang bikin video "review website MA", tapi banyak yang
# bikin video "cara pakai e-court" / "cara cari putusan online" - dan komentar di video
# kayak gini paling sering isinya keluhan proses ("error pas login", "gak nemu
# fiturnya", dll), bukan opini institusional.
# SENGAJA dicari LINTAS SEMUA KANAL (gak lewat CHANNEL_HANDLES) karena tutorial gini
# biasanya dibikin creator individu/kanal edukasi hukum, bukan media besar.
WEBSITE_KEYWORDS = [
    "cara cari putusan online Mahkamah Agung",
    "tutorial e-court Indonesia",
    "cara daftar e-court",
    "cara download putusan MA",
    "tutorial SIPP pengadilan",
    "cara cek jadwal sidang online",
    "cara pakai aplikasi SIPP",
]

# Term wajib buat video kategori INSTITUSIONAL (hasil dari KEYWORDS): title cuma
# lolos kalau ngandung minimal SATU dari term ini (case-insensitive, substring match).
#
# SENGAJA DIPERKETAT: sebelumnya list ini penuh istilah hukum GENERIK ("putusan",
# "hakim", "pengadilan", "yudisial", "praperadilan") - masalahnya semua istilah itu
# dipake di SEMUA level pengadilan (PN, PT) dan institusi lain (Kejaksaan, Komisi
# Yudisial, dst), bukan eksklusif Mahkamah Agung. Channel berita nge-tag video pake
# istilah hukum umum buat SEO, jadi video yang gak ada hubungannya sama MA ikut lolos
# selama nyebut kata hukum apapun. Sekarang cuma term yang SPESIFIK/EKSKLUSIF ranah
# Mahkamah Agung yang dianggap cukup buat lolos filter.
INSTITUTIONAL_RELEVANCE_TERMS = [
    "mahkamah agung",
    "ma",  # ditangani lewat regex word-boundary di scraper, bukan substring literal
    "kasasi",              # proses hukum yang eksklusif ranah Mahkamah Agung
    "peninjauan kembali",  # PK - eksklusif ranah Mahkamah Agung
]

# Term wajib KHUSUS video kategori TUTORIAL_WEBSITE (hasil dari WEBSITE_KEYWORDS).
# TERPISAH dari INSTITUTIONAL_RELEVANCE_TERMS dengan sengaja: video tutorial "cara
# pakai e-court" / "tutorial SIPP" HAMPIR GAK PERNAH nyebut "Mahkamah Agung" atau
# "MA" secara eksplisit di title, walaupun e-Court dan SIPP itu sistem yang
# dijalanin di bawah Mahkamah Agung. Kalau dipaksa pake filter yang sama kayak
# institusional, semua video tutorial ke-buang dan hasilnya nol.
WEBSITE_RELEVANCE_TERMS = [
    "mahkamah agung",
    "ma",
    "e-court",
    "ecourt",
    "sipp",
    "putusan online",
    "direktori putusan",
    "cari putusan",
]

# Video dibuang kalau title-nya ngandung salah satu term ini DAN gak nyebut
# "mahkamah agung"/" ma " secara eksplisit. Ini nyaring konten Mahkamah Konstitusi
# (MK) yang suka ke-tarik ikutan karena sama-sama pake kata umum "putusan",
# "hakim", "pengadilan", dll.
EXCLUDE_TERMS = [
    "mahkamah konstitusi",
    "hakim konstitusi",
    "mk ri",
    "puu-",  # format nomor perkara uji materi UU, khas MK (mis. "243/PUU-XXIV/2026")
]

# Term buat nge-flag komentar yang BENERAN ngebahas pengalaman pakai website/aplikasi
# (bukan cuma nyebut nama produk atau ngomongin kasus hukum). Dipake buat ngisi kolom
# mentions_website_experience di CSV komentar - True/False, gak dibuang, tinggal
# difilter pas analisis (misal di Excel/pandas: filter True doang).
COMMENT_EXPERIENCE_TERMS = [
    "error",
    "eror",
    "gagal",
    "lemot",
    "lambat",
    "down",
    "maintenance",
    "gak bisa dibuka",
    "ga bisa dibuka",
    "tidak bisa diakses",
    "susah diakses",
    "susah dicari",
    "ribet",
    "loading",
    "server",
    "gagal login",
    "gagal upload",
    "situsnya",
    "webnya",
    "web nya",
    "aplikasinya",
    "aplikasi nya",
]

# (Opsional) batasi pencarian YouTube ke kanal berita tertentu biar hasil lebih representatif
# publik umum. Cuma dipake buat KEYWORDS (institusional) - WEBSITE_KEYWORDS selalu lintas kanal.
# Kosongkan list ini kalau mau search lintas semua kanal buat KEYWORDS juga.
# CATATAN: kalau diisi, quota search terpakai per-channel (dikali jumlah channel),
# jadi kurangin MAX_VIDEOS_PER_KEYWORD kalau quota mepet.
CHANNEL_HANDLES = [

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

# Batas jumlah komentar yang ditarik per post Reddit
MAX_COMMENTS_PER_POST = 200