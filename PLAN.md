# Rencana Transformasi Scraper: Pelacakan Tren Reputasi Mahkamah Agung (2020–2026)

Dokumen ini merinci rencana perubahan arsitektur, parameter data, taksonomi kata kunci, serta alur analisis agar scraper ini mampu mengumpulkan, menstrukturkan, dan menyajikan data perkembangan reputasi Mahkamah Agung (MA) secara longitudinal dari tahun 2020 hingga 2026.

---

## 1. Pertimbangan Utama & Keterbatasan Platform

### A. Kuota YouTube Data API v3 (10.000 unit/hari)
* Panggilan `youtube.search().list` mengonsumsi **100 unit/call**.
* Jika mencari 15 kata kunci untuk 7 tahun berbeda (2020 s.d. 2026), kebutuhan kuota mencapai:
  $$\text{15 kata kunci} \times \text{7 tahun} \times 100\text{ unit} = 10.500\text{ unit}$$
  (Ini langsung melewati batas harian default).
* **Solusi Rencana:**
  * Implementasi eksekusi per tahun via CLI (misalnya `--year 2022`).
  * Penyimpanan cache hasil pencarian mentah per tahun (`output/_raw_search_cache_{year}.json`).
  * Optimasi daftar kata kunci prioritas untuk menjaga efisiensi kuota.

### B. Keterbatasan Data Historis Reddit (PRAW)
* Reddit API tidak memiliki parameter rentang tanggal spesifik (`publishedBefore` / `publishedAfter`).
* Opsi `time_filter="all"` hanya mengembalikan maksimal 250–1.000 submission terpopuler sepanjang masa.
* **Solusi Rencana:**
  * Menarik data dengan `time_filter="all"`, lalu melakukan validasi dan pemfilteran timestamp (`created_utc`) pada level kode.
  * Mengubah mode penyimpanan CSV dari *overwrite* (`"w"`) menjadi *append* (`"a"`) dengan pemeriksaan ID agar data historis lama tidak hilang.

---

## 2. Rencana Perubahan Komponen

### A. Konfigurasi & Taksonomi Isu (`config.py`)
1. **Parameter Waktu Multi-Tahun:**
   * Menambahkan konfigurasi rentang tahun:
     ```python
     START_YEAR = 2020
     END_YEAR = 2026
     ```
   * Menggantikan pembatasan kaku `DAYS_LOOKBACK = 180` menjadi rentang dinamis berbasis tahun/tanggal.
2. **Pengelompokan Kata Kunci Berbasis Dimensi Reputasi & Milestone Kasus:**
   * **Integritas & Skandal Peradilan:**
     `"suap Mahkamah Agung"`, `"OTT hakim agung"`, `"mafia peradilan MA"`, `"Nurhadi MA"`, `"Hasbi Hasan MA"`, `"Zarof Ricar"`
   * **Kinerja Putusan & Keadilan Substantif:**
     `"kasasi MA"`, `"peninjauan kembali MA"`, `"diskon hukuman MA"`, `"vonis bebas kasasi MA"`, `"putusan MA pilkada"`
   * **Layanan Publik & Akuntabilitas (UX / Sistem):**
     `"e-court Mahkamah Agung"`, `"direktori putusan MA"`, `"SIPP pengadilan"`, `"jadwal sidang online MA"`
3. **Kategori Isu Otomatis:**
   * Memberikan label kategori spesifik pada output: `integritas_korupsi`, `putusan_kontroversial`, dan `layanan_digital_ux`.

---

### B. YouTube Scraper (`youtube_scraper.py`)
1. **Penerapan *Temporal Slicing*:**
   * Modifikasi fungsi `search_videos` agar menerima parameter `start_date` dan `end_date` (format RFC 3339).
   * Memungkinkan pencarian dipartisi per tahun (misal: 1 Jan 2021 – 31 Des 2021).
2. **Dukungan Argumen CLI:**
   * Penambahan argumen untuk menjalankan scraper pada tahun tertentu:
     ```bash
     python youtube_scraper.py --year 2023
     python youtube_scraper.py --start-year 2020 --end-year 2026
     ```
3. **Pengayaan Metadata Waktu pada CSV:**
   * Menambahkan kolom `published_year` dan `published_month` pada `youtube_videos.csv` dan `youtube_comments.csv` untuk mempermudah agregasi tren berkala.
4. **Deduplikasi & Mekanisme Resume:**
   * Menjamin data lama tidak terhapus saat menjalankan pencarian tahun baru.

---

### C. Reddit Scraper (`reddit_scraper.py`)
1. **Mode Append & Deduplikasi:**
   * Mengubah mekanisme penyimpanan CSV dari overwrite ke append dengan validasi `post_id` dan `comment_id`.
2. **Ekstraksi Waktu:**
   * Mengonversi `created_utc` ke dalam format tanggal terbaca serta menambahkan field `created_year` dan `created_month`.
3. **Filter Rentang Waktu:**
   * Hanya menyimpan post dan komentar yang dibuat dalam interval tahun 2020–2026.

---

### D. Runner Utama (`main.py`)
* Menambahkan opsi meneruskan argumen tahun ke masing-masing scraper:
  ```bash
  python main.py --yt --year 2022
  python main.py --all --start-year 2020 --end-year 2026
  ```

---

### E. Modul Analisis & Visualisasi Tren Reputasi (`analyze_reputation.py` - Baru)
Script downstream untuk mengolah data gabungan dari CSV:
1. **Tren Volume Percakapan:** Menghitung jumlah video, post, dan komentar per tahun/bulan untuk melihat kapan MA menjadi sorotan tertinggi.
2. **Tren Rasio Sentimen:** Menghitung perbandingan sentimen (Positif, Netral, Negatif) sepanjang rentang 2020–2026.
3. **Korelasi Peristiwa (*Event-Driven Spikes*):** Mengaitkan lonjakan sentimen negatif pada tahun tertentu dengan kasus besar yang terjadi pada periode tersebut.
4. **Ekspor Ringkasan:** Menghasilkan tabel ringkasan `output/reputation_trend_2020_2026.csv` dan grafik tren.

---

## 3. Rencana Pengujian & Verifikasi

1. **Uji Jendela Waktu (Dry-Run):**
   * Menjalankan pencarian YouTube untuk tahun `2021` dengan kuota minimal (`max_results=2`) untuk memverifikasi bahwa video yang terjaring memiliki `published_at` tepat pada tahun 2021.
2. **Uji Integritas File CSV:**
   * Menjalankan scraper dua kali pada periode yang sama dan memverifikasi tidak ada duplikasi data atau penimpaan file secara tidak sengaja.
3. **Uji Filter Timestamp Reddit:**
   * Memastikan post Reddit yang lolos filter berada dalam rentang tahun 2020–2026.
