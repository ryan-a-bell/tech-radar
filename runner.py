#!/usr/bin/env python3
"""
runner.py — the daily/weekly discovery job.

  python runner.py            # run all scrapers, then build radar.json
  python runner.py --build    # only rebuild radar.json from items/
  python runner.py --dry-run  # discover + report, write nothing

The runner discovers only. It writes ring="Discovered" items and never
touches a technology a human has already classified (dedup by file
existence). A re-seen item only gets its last_seen refreshed.
"""

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radar_core as core  # noqa: E402

# register scrapers here — adding a source is one line.
from scrapers.github_trending import GitHubTrendingScraper  # noqa: E402
from scrapers.rss_feeds import RSSFeedScraper  # noqa: E402
from scrapers.reddit import RedditScraper  # noqa: E402

SCRAPERS = [
    GitHubTrendingScraper(limit=25),
    RSSFeedScraper(per_feed=15),
    RedditScraper(per_sub=10),
]


def save_raw(scraper_name, items, day):
    """Dump untouched scrape output — the audit trail / replay buffer."""
    folder = os.path.join(core.RAW_DIR, day)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{scraper_name}.json"), "w") as f:
        json.dump(items, f, indent=2)


def build_radar_json():
    """Aggregate all per-tech files into the single file the dashboard reads.
    Adds a computed 'trend' field (up/down/flat/none) from star history."""
    items = core.load_all_items()
    for it in items:
        direction, delta = core.star_trend(it)
        it["trend"] = direction          # up | down | flat | none
        it["trend_delta"] = delta        # +/- stars over the window
    items.sort(key=lambda x: (x.get("first_seen", ""), x["name"]), reverse=True)
    payload = {
        "generated": date.today().isoformat(),
        "count": len(items),
        "items": items,
    }
    os.makedirs(os.path.dirname(core.RADAR_JSON), exist_ok=True)
    with open(core.RADAR_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    return len(items)


def run(dry_run=False):
    today = date.today().isoformat()
    stats = {"new": 0, "known": 0, "merged": 0, "errors": 0}

    # canonical-url index, built once per run. Lets us detect that a tech
    # found via Reddit is the same repo we already store under GitHub.
    canon = core.canonical_index()

    print(f"=== discovery run {today} ===")
    for scraper in SCRAPERS:
        try:
            found = scraper.discover()
        except Exception as e:
            print(f"  ! {scraper.name} failed: {e}")
            stats["errors"] += 1
            continue

        if not dry_run:
            save_raw(scraper.name, found, today)

        new_here = 0
        merged_here = 0
        for item in found:
            cu = item.get("canonical_url")
            if core.exists(item["id"]):
                # already known under this exact source+key
                stats["known"] += 1
                if not dry_run:
                    s = item.get("stars") or None
                    core.touch_last_seen(item["id"], today, stars=s)
            elif cu and cu in canon:
                # SAME tech, DIFFERENT source — merge, don't duplicate
                stats["merged"] += 1
                merged_here += 1
                if not dry_run:
                    core.record_also_seen(canon[cu], item["source"],
                                          item["url"], today)
            else:
                # genuinely new technology
                stats["new"] += 1
                new_here += 1
                if not dry_run:
                    core.save_new(item)
                    if cu:                       # index it for later sources
                        canon[cu] = item["id"]
        print(f"  {scraper.name:12s} {len(found):3d} found  "
              f"{new_here:3d} new  {merged_here:3d} merged")

    print(f"--- totals: {stats['new']} new, {stats['known']} known, "
          f"{stats['merged']} cross-source merges, "
          f"{stats['errors']} scraper errors")

    if not dry_run:
        total = build_radar_json()
        print(f"--- built radar.json ({total} technologies)")
    else:
        print("--- dry run: nothing written")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true",
                    help="only rebuild radar.json, skip scraping")
    ap.add_argument("--dry-run", action="store_true",
                    help="discover and report, write nothing")
    args = ap.parse_args()

    if args.build:
        n = build_radar_json()
        print(f"built radar.json ({n} technologies)")
    else:
        run(dry_run=args.dry_run)
