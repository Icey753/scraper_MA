"""
Runner utama - jalanin YouTube dan Reddit scraper sekaligus.
Usage:
    python main.py                  # jalanin dua-duanya
    python main.py --yt              # cuma YouTube
    python main.py --reddit          # cuma Reddit
    python main.py --yt --year 2022  # YouTube, slice tahun kalender 2022
"""

import argparse

import youtube_scraper
import reddit_scraper
import config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yt", action="store_true", help="Cuma jalanin YouTube scraper")
    parser.add_argument("--reddit", action="store_true", help="Cuma jalanin Reddit scraper")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Diterusin ke youtube_scraper buat slice satu tahun kalender "
        "(Reddit gak bisa di-slice per tahun, diabaikan buat --reddit).",
    )
    args = parser.parse_args()

    run_yt = not args.reddit
    run_reddit = not args.yt

    if args.year is not None and not (config.START_YEAR <= args.year <= config.END_YEAR):
        parser.error(f"--year harus di antara {config.START_YEAR}-{config.END_YEAR}")

    if run_yt:
        print("=== Menjalankan YouTube scraper ===")
        youtube_scraper.run(year=args.year)

    if run_reddit:
        print("=== Menjalankan Reddit scraper ===")
        reddit_scraper.run()


if __name__ == "__main__":
    main()
