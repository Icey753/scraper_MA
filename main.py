"""
Runner utama - jalanin YouTube dan Reddit scraper sekaligus.
Usage:
    python main.py            # jalanin dua-duanya
    python main.py --yt        # cuma YouTube
    python main.py --reddit    # cuma Reddit
"""

import sys
import youtube_scraper
import reddit_scraper


def main():
    args = sys.argv[1:]

    run_yt = "--reddit" not in args
    run_reddit = "--yt" not in args

    if run_yt:
        print("=== Menjalankan YouTube scraper ===")
        youtube_scraper.run()

    if run_reddit:
        print("=== Menjalankan Reddit scraper ===")
        reddit_scraper.run()


if __name__ == "__main__":
    main()
