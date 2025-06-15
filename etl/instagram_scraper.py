#!/usr/bin/env python3
# etl/instagram_scraper.py

import os
import re
import json
import argparse
import requests
from dotenv import load_dotenv

from api.models import SessionLocal, init_db
from api.crud   import create_influencer

# ————————————————
# 1) HTML-ONLY HASHTAG SCRAPE
# ————————————————
def fetch_profiles_by_hashtag(tag: str, max_results: int) -> list[dict]:
    """
    Scrape the public hashtag page and pull out poster usernames.
    Metrics (followers, posts) are left None.
    """
    url = f"https://www.instagram.com/explore/tags/{tag}/"
    resp = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible)"
    })
    resp.raise_for_status()
    html = resp.text

    # extract the JSON from window._sharedData
    m = re.search(r"window\._sharedData = (.*?);</script>", html)
    if not m:
        raise RuntimeError("Could not find sharedData in IG page")
    data = json.loads(m.group(1))

    # navigate to the list of recent posts
    edges = (
        data["entry_data"]["TagPage"][0]
            ["graphql"]["hashtag"]
            ["edge_hashtag_to_media"]["edges"]
    )

    seen = set()
    out  = []
    for edge in edges:
        user = edge["node"]["owner"]["username"]
        if user in seen:
            continue
        seen.add(user)
        out.append({
            "id":               f"IG:{user}",
            "title":            user,
            "description":      None,
            "published_at":     None,
            "subscriber_count": None,   # optional: you could scrape profile page later
            "view_count":       None,
            "video_count":      None,
        })
        if len(out) >= max_results:
            break

    return out


# ————————————————
# 2) LOAD INTO DB
# ————————————————
def load_to_db(tag: str, max_results: int) -> None:
    init_db()
    db = SessionLocal()
    try:
        for prof in fetch_profiles_by_hashtag(tag, max_results):
            create_influencer(db, prof)
    finally:
        db.close()


# ————————————————
# 3) CLI
# ————————————————
if __name__ == "__main__":
    load_dotenv()

    p = argparse.ArgumentParser(
        description="Instagram scraper + DB loader (hashtag, HTML-only)"
    )
    p.add_argument("--hashtag", required=True, help="Hashtag (no #)")
    p.add_argument("--max",     type=int, default=10, help="Max profiles to fetch")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON instead of inserting into DB"
    )
    args = p.parse_args()

    if args.dry_run:
        data = fetch_profiles_by_hashtag(args.hashtag, args.max)
        print(json.dumps(data, indent=2))
    else:
        load_to_db(args.hashtag, args.max)
        print(f"✅ Scraped & loaded IG #{args.hashtag} profiles into DB")
