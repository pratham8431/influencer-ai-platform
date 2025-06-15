#!/usr/bin/env python3
# etl/youtube_scraper.py

import os
import json
import argparse
import itertools
from collections import Counter

import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors   import HttpError
from dotenv                   import load_dotenv

from api.models import SessionLocal, init_db
from api.crud   import create_influencer

# ————————————————
# 1) ROTATING API-KEY SETUP
# ————————————————
load_dotenv()  # loads .env from project root
API_KEYS = os.getenv("YOUTUBE_API_KEYS", "").split(",")
if not API_KEYS or API_KEYS == [""]:
    raise RuntimeError("Set YOUTUBE_API_KEYS in .env (comma-separated)")
_key_cycle = itertools.cycle(API_KEYS)

def get_youtube_client():
    """Pull the next key and return a new YouTube client."""
    key = next(_key_cycle)
    return build("youtube", "v3", developerKey=key)


# ————————————————
# 2) HTML FALLBACK SCRAPER
# ————————————————
# etl/youtube_scraper.py (near top, under imports)

import re
from urllib.parse import quote_plus

def scrape_channel_ids_from_html(query: str, max_results: int) -> list[str]:
    """
    Fetch YouTube search HTML and extract channel IDs from /channel/ and /c/ URLs.
    """
    url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
    r   = requests.get(url)
    r.raise_for_status()

    text = r.text
    # find both /channel/UCxxx and /c/CustomName patterns:
    ids = re.findall(r'/(?:channel|c)/([A-Za-z0-9_\-]+)', text)
    # keep only unique, preserve order
    seen = set()
    out = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
        if len(out) >= max_results:
            break
    return out



# ————————————————
# 3) BATCH CHANNEL STATS FETCH
# ————————————————
def fetch_channel_stats_batch(channel_ids: list[str]) -> list[dict]:
    """Fetch snippet+statistics for up to 50 channels in one API call."""
    if not channel_ids:
        return []

    client = get_youtube_client()
    try:
        resp = client.channels().list(
            part="snippet,statistics",
            id=",".join(channel_ids)
        ).execute()

    except HttpError as e:
        body = e.content.decode(errors="ignore")
        if e.resp.status == 403 and "quotaExceeded" in body:
            # rotate key & retry once
            client = get_youtube_client()
            resp   = client.channels().list(
                part="snippet,statistics",
                id=",".join(channel_ids)
            ).execute()
        else:
            raise

    out = []
    for item in resp.get("items", []):
        sn = item["snippet"]
        st = item["statistics"]
        out.append({
            "id":               item["id"],
            "title":            sn["title"],
            "description":      sn.get("description", ""),
            "published_at":     sn["publishedAt"],
            "subscriber_count": int(st.get("subscriberCount", 0)),
            "view_count":       int(st.get("viewCount", 0)),
            "video_count":      int(st.get("videoCount", 0)),
        })
    return out


# ————————————————
# 4) SEARCH MODES (with full quota-rotation)
# ————————————————
def search_channels_by_name(query: str, max_results: int = 10) -> list[dict]:
    """
    Rotate through API keys to search by channel name.
    Falls back to HTML scrape only if *all* keys are over quota.
    """
    last_exc = None
    for _ in range(len(API_KEYS)):
        client = get_youtube_client()
        try:
            resp = client.search().list(
                q=query, part="snippet", type="channel", maxResults=max_results
            ).execute()
            cids = [itm["snippet"]["channelId"] for itm in resp.get("items", [])]
            return fetch_channel_stats_batch(cids)

        except HttpError as e:
            body = e.content.decode(errors="ignore")
            if e.resp.status == 403 and "quotaExceeded" in body:
                last_exc = e
                continue
            raise

    # all keys exhausted → HTML fallback
    print("⚠️ All keys over quota. Falling back to HTML channel scrape.")
    ids = scrape_channel_ids_from_html(query, max_results)
    return fetch_channel_stats_batch(ids)


def search_channels_by_video(query: str, max_results: int = 50) -> list[dict]:
    """
    Rotate through API keys to search by video relevance.
    Falls back to HTML scrape only if all keys are over quota.
    """
    last_exc = None
    for _ in range(len(API_KEYS)):
        client = get_youtube_client()
        try:
            resp = client.search().list(
                q=query, part="snippet", type="video", maxResults=max_results
            ).execute()
            counts  = Counter(itm["snippet"]["channelId"] for itm in resp.get("items", []))
            top_cids = [cid for cid, _ in counts.most_common(max_results)]
            return fetch_channel_stats_batch(top_cids)

        except HttpError as e:
            body = e.content.decode(errors="ignore")
            if e.resp.status == 403 and "quotaExceeded" in body:
                last_exc = e
                continue
            raise

    # all keys exhausted → HTML fallback
    print("⚠️ All keys over quota. Falling back to HTML video scrape.")
    ids = scrape_channel_ids_from_html(query, max_results)
    return fetch_channel_stats_batch(ids)


def fetch_channels(query: str, max_results: int, method: str) -> list[dict]:
    """Dispatch based on the `--method` flag."""
    if method == "video":
        return search_channels_by_video(query, max_results)
    return search_channels_by_name(query, max_results)


# ————————————————
# 5) LOAD INTO DB
# ————————————————
def load_to_db(keyword: str, max_results: int, method: str) -> None:
    init_db()
    db = SessionLocal()
    try:
        for ch in fetch_channels(keyword, max_results, method):
            create_influencer(db, {
                "id":               ch["id"],
                "title":            ch["title"],
                "description":      ch["description"],
                "published_at":     ch["published_at"],
                "subscriber_count": ch["subscriber_count"],
                "view_count":       ch["view_count"],
                "video_count":      ch["video_count"],
            })
    finally:
        db.close()


# ————————————————
# 6) CLI ENTRYPOINT
# ————————————————
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YouTube scraper + DB loader (channel or video mode)"
    )
    parser.add_argument("--keyword", required=True, help="Search term for influencers")
    parser.add_argument("--max",     type=int, default=10, help="How many to scrape")
    parser.add_argument(
        "--method",
        choices=["channel", "video"],
        default="channel",
        help="‘channel’ or ‘video’ search mode"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON instead of inserting into DB"
    )
    args = parser.parse_args()

    if args.dry_run:
        out = fetch_channels(args.keyword, args.max, args.method)
        print(json.dumps(out, indent=2))
    else:
        load_to_db(args.keyword, args.max, args.method)
        print(f"✅ Scraped ({args.method}) and loaded into DB")
