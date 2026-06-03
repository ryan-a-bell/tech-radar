"""
scrapers/rss_feeds.py — RSS/Atom feed scraper.

Not yet implemented. Returns an empty list so runner.py loads without
errors. Replace discover() with real feed parsing when ready.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.base import Scraper  # noqa: E402


class RSSFeedScraper(Scraper):
    name = "rss"

    def __init__(self, per_feed=15):
        self.per_feed = per_feed

    def discover(self):
        return []
