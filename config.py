"""
Config terpusat: keyword list, target channel, dan parameter waktu.
Edit KEYWORDS dan CHANNEL_HANDLES sesuai isu yang lagi mau di-track.
"""

# Keyword institusional - isu hukum & reputasi MA secara umum. Dibatasi ke kanal
# berita (lihat CHANNEL_HANDLES) biar hasilnya representatif publik umum.
#
# Dikelompokkan per dimensi reputasi biar tiap video/post/comment yang ketarik
# otomatis kebawa label "dimension"-nya - dipake buat nyusun tren reputasi per
# tahun di analyze_reputation.py, tanpa perlu topic modeling terpisah (data
# komentar publik terlalu noisy buat unsupervised topic modeling yang koheren).
KEYWORDS = {
    "integritas_korupsi": [
        "suap Mahkamah Agung",
        "mafia peradilan",
        "kode etik hakim agung",
        "OTT hakim agung",
        # Nama kasus/tersangka spesifik - yield lebih tinggi daripada istilah
        # generik karena ini kasus besar yang banyak diberitakan.
        "Zarof Ricar",
        "Hasbi Hasan MA",
        "Nurhadi MA",
        "Sudrajad Dimyati",
        "Gazalba Saleh",
        "vonis bebas kasasi MA",
        "diskon hukuman MA",
        "gratifikasi hakim agung",
        "makelar kasus MA",
    ],
    "putusan_kontroversial": [
        "putusan Mahkamah Agung",
        "vonis MA",
        "kasasi MA",
        "peninjauan kembali MA",
        "putusan MA pilkada",
    ],
    "layanan_digital_ux": [
        "direktori putusan MA",
        "e-court Mahkamah Agung",
        "SIPP pengadilan",
    ],
    # Dimensi baru: persepsi/kepercayaan publik ke MA secara institusional -
    # fokus riset digeser dari UI/UX ke reputasi keseluruhan + kemauan publik
    # pakai kanal resmi (lihat diskusi tim: warga jarang beneran pakai
    # websitenya, opininya kebentuk dari framing media soal skandal/putusan).
    "kepercayaan_publik": [
        "kepercayaan publik Mahkamah Agung",
        "citra Mahkamah Agung",
        "reputasi Mahkamah Agung",
        "gak percaya Mahkamah Agung",
        "percuma lapor MA",
        "transparansi Mahkamah Agung",
        "akuntabilitas MA",
        "kecewa putusan MA",
        "hukum tumpul ke atas",
    ],
}

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
    # Sikap/kemauan pakai kanal digital resmi - sengaja diarahin ke istilah
    # spesifik e-court/SIPP/sidang online (bukan "aplikasi pemerintah" generik)
    # biar tetep lolos WEBSITE_RELEVANCE_TERMS, bukan nyasar ke aplikasi
    # pemerintah lain (Pajak, Dukcapil, dst).
    "males pake e-court",
    "ribet aplikasi SIPP",
    "gak percaya sistem pengadilan online",
    "mending sidang manual daripada online",
    "data pribadi aman gak e-court",
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
    "hakim agung",  # jabatan eksklusif MA - video soal ini sering gak nyebut "MA"/"Mahkamah Agung" lagi di title
    # Nama tersangka/kasus skandal MA - proper noun unik, gak perlu embel-embel
    # "Mahkamah Agung"/"MA" di title buat dianggap relevan.
    "zarof ricar",
    "hasbi hasan",
    "nurhadi",
    "sudrajad dimyati",
    "gazalba saleh",
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

# Rentang waktu (dalam hari ke belakang dari hari ini) buat filter YouTube publishedAfter -
# dipake kalau youtube_scraper.py dijalanin TANPA --year (mode "scan terbaru" lama).
DAYS_LOOKBACK = 180

# Rentang tahun buat tracking tren reputasi longitudinal. Dipake sebagai referensi
# validasi (Reddit) dan batas wajar buat --year di youtube_scraper.py.
START_YEAR = 2020
END_YEAR = 2026

# Reddit time_filter: hour, day, week, month, year, all
REDDIT_TIME_FILTER = "year"

# Batas jumlah video per keyword (jaga quota YouTube API - search = 100 unit/call)
MAX_VIDEOS_PER_KEYWORD = 15

# Batas jumlah post per keyword per subreddit (Reddit search)
MAX_POSTS_PER_KEYWORD = 50

# Batas jumlah komentar yang ditarik per post Reddit
MAX_COMMENTS_PER_POST = 200