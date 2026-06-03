"""
scrapers/reddit.py — discover tech surfacing on Reddit.

Uses Reddit's public .json endpoints — no API key, no OAuth. Just needs
a descriptive User-Agent (Reddit blocks generic ones).

Momentum is derived from upvote score. Reddit rarely tells us a vendor,
so company is left None unless the title obviously names one.
"""

import sys
import os
import json
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar_core import new_item  # noqa: E402
from scrapers.base import Scraper  # noqa: E402

UA = "tech-radar-bot/1.0 (discovery; contact: radar@example.com)"

# (subreddit, quadrant hint). Pulls /top this week from each.
SUBS = [
    ("programming", "Tools"),
    ("rust", "Languages"),
    ("MachineLearning", "Techniques"),
    ("devops", "Platforms"),
    ("selfhosted", "Platforms"),
]


class RedditScraper(Scraper):
    name = "reddit"

    def __init__(self, subs=None, per_sub=10, min_score=150):
        self.subs = subs or SUBS
        self.per_sub = per_sub
        self.min_score = min_score   # ignore low-engagement noise

    def discover(self):
        items = []
        for sub, quadrant in self.subs:
            url = (f"https://www.reddit.com/r/{sub}/top.json"
                   f"?t=week&limit={self.per_sub}")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.load(resp)
            except Exception as e:
                print(f"  ! r/{sub} failed: {e}", file=sys.stderr)
                continue

            for child in payload.get("data", {}).get("children", []):
                post = child.get("data", {})
                score = post.get("score", 0)
                if score < self.min_score:
                    continue
                title = post.get("title", "").strip()
                # prefer the linked URL over the reddit comment thread
                link = post.get("url_overridden_by_dest") or \
                    ("https://reddit.com" + post.get("permalink", ""))
                permalink = "https://reddit.com" + post.get("permalink", "")
                if not title:
                    continue
                # momentum: scale score onto 0-100 (1000+ upvotes = maxed)
                momentum = min(100, score // 10)
                desc = (post.get("selftext", "")[:300].strip()
                        or f"Discussed on r/{sub} with {score} upvotes.")
                items.append(new_item(
                    source="Reddit",
                    key=post.get("id", permalink),
                    name=title[:120],
                    description=desc,
                    url=permalink,         # the discussion thread
                    linked_url=link,       # often a GitHub repo → enables dedup
                    quadrant=quadrant,
                    momentum=momentum,
                    tags=[f"r/{sub}"],
                    company=None,   # Reddit doesn't reliably tell us a vendor
                ))
        return items


if __name__ == "__main__":
    for it in RedditScraper(per_sub=3).discover():
        print(it["id"][:50], "->", it["name"][:50])
