# MA Sentiment Scraper

Scraper buat ngumpulin data teks publik (video + komentar YouTube, post + komentar Reddit) seputar isu hukum yang berkaitan dengan Mahkamah Agung — dipake sebagai data pendukung analisis UX/HCI untuk revisi website mahkamahagung.go.id.

Pake API resmi (YouTube Data API v3 & Reddit API via PRAW) — bukan browser automation — jadi lebih stabil dan gratis dalam batas quota harian.

## Struktur

```
ma-sentiment-scraper/
├── config.py              # keyword list, channel, subreddit, parameter waktu
├── youtube_scraper.py      # search video + tarik comment threads
├── reddit_scraper.py       # search post lintas subreddit + tarik komentar
├── main.py                 # runner (jalanin salah satu atau dua-duanya)
├── requirements.txt
├── .env.example             # template kredensial API
├── output/                  # hasil scrape (CSV, di-gitignore)
└── logs/                    # log tiap run (di-gitignore)
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` jadi `.env`, isi kredensial:
   ```bash
   cp .env.example .env
   ```

   **YouTube API key:**
   - Buka [Google Cloud Console](https://console.cloud.google.com/)
   - Bikin project baru (atau pake yang udah ada), aktifkan **YouTube Data API v3**
   - Bikin credential tipe **API Key**, copy ke `YOUTUBE_API_KEY`
   - Quota default: 10.000 unit/hari (search = 100 unit/call, comment list = 1 unit/call)

   **Reddit API credentials:**
   - Buka [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
   - Klik "create app", pilih tipe **script**
   - `REDDIT_CLIENT_ID` = string di bawah nama app
   - `REDDIT_CLIENT_SECRET` = "secret"
   - `REDDIT_USER_AGENT` = bebas, tapi wajib ada format `<nama app> by u/<username>`

3. Edit `config.py` — sesuaikan `KEYWORDS`, `CHANNEL_HANDLES`, `SUBREDDITS`, dan rentang waktu sesuai isu yang mau di-track.

## Menjalankan

```bash
python main.py              # jalanin YouTube + Reddit
python main.py --yt          # cuma YouTube
python main.py --reddit      # cuma Reddit
```

Output CSV masuk ke folder `output/`:
- `youtube_videos.csv`, `youtube_comments.csv`
- `reddit_posts.csv`, `reddit_comments.csv`

Log tiap run ada di folder `logs/`.

## Catatan quota & etika scraping

- **YouTube**: `search()` mahal (100 unit/call). Jangan taruh terlalu banyak keyword atau naikin `MAX_VIDEOS_PER_KEYWORD` sembarangan kalau gak mau kena limit harian. Comment list murah, jadi aman di-loop sering.
- **Reddit**: PRAW otomatis handle rate limiting sesuai batas resmi API (biasanya ~60 request/menit buat OAuth script app), gak perlu delay manual yang agresif, tapi kode ini tetep kasih jeda kecil (`time.sleep`) buat jaga-jaga.
- Data yang ditarik cuma teks publik yang emang visible tanpa login — tetep hormati Terms of Service masing-masing platform, terutama soal penyimpanan dan republikasi data.
- Kalau tujuan risetnya analisis UX (bukan cuma sentimen), tambahin keyword yang eksplisit soal keluhan teknis website (contoh sudah ada di `config.py`: "susah akses putusan MA", "website Mahkamah Agung") biar data yang ketarik lebih actionable buat bagian revisi desain.

## Next steps yang mungkin lo butuhin

- Tambahin script sentiment labeling / kategorisasi isu (misal pake IndoBERT atau keyword-based tagging) buat tahap analisis
- Convert CSV output ke format yang gampang di-import ke tool riset UX (affinity diagram, tabel pain point, dll)
