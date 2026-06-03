"""
scrapers/github_trending.py — discover trending repos.

Scrapes the public GitHub Trending page. No API key, no auth.
Momentum = stars gained in the period (GitHub reports this directly).
"""

import re
import sys
import os
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from radar_core import new_item  # noqa: E402
from scrapers.base import Scraper  # noqa: E402

TRENDING_URL = "https://github.com/trending?since=daily"
UA = "tech-radar-bot/1.0 (+discovery)"

# crude quadrant hints from language / topic
_LANG_QUADRANT = {
    "rust": "Languages", "go": "Languages", "python": "Languages",
    "zig": "Languages", "elixir": "Languages", "typescript": "Languages",
}

# GitHub orgs that are recognizable companies. The repo owner (the part
# before the "/") is matched against this map. Community orgs and personal
# accounts stay company=None. Extend this list as you encounter vendors.
_KNOWN_COMPANIES = {
    "anthropics": "Anthropic", "openai": "OpenAI", "google": "Google",
    "google-deepmind": "Google DeepMind", "microsoft": "Microsoft",
    "dotnet": "Microsoft", "vercel": "Vercel", "meta": "Meta",
    "facebook": "Meta", "aws": "Amazon", "awslabs": "Amazon",
    "cloudflare": "Cloudflare", "netflix": "Netflix", "uber": "Uber",
    "stripe": "Stripe", "shopify": "Shopify", "apple": "Apple",
    "nvidia": "NVIDIA", "nvlabs": "NVIDIA", "huggingface": "Hugging Face",
    "supabase": "Supabase", "vuejs": "Vue", "oven-sh": "Oven",
    "astral-sh": "Astral", "denoland": "Deno", "tursodatabase": "Turso",
    "modular": "Modular", "elastic": "Elastic", "grafana": "Grafana",
    "hashicorp": "HashiCorp", "jetbrains": "JetBrains", "redis": "Redis",
    "mongodb": "MongoDB", "docker": "Docker", "gitlab": "GitLab",
    "zed-industries": "Zed Industries", "tauri-apps": "Tauri",
}


class _TrendingParser(HTMLParser):
    """Pulls repo rows out of the trending page HTML."""
    def __init__(self):
        super().__init__()
        self.repos = []
        self._cur = None
        self._capture = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")
        if tag == "h2" and "lh-condensed" in cls:
            self._cur = {"slug": "", "desc": "", "lang": "", "stars": 0,
                         "period_stars": 0}
        elif tag == "a" and self._cur is not None and not self._cur["slug"]:
            href = a.get("href", "")
            if href.count("/") == 2:
                self._cur["slug"] = href.strip("/")
        elif tag == "p" and self._cur is not None and "col-9" in cls:
            self._capture = "desc"
        elif tag == "span" and a.get("itemprop") == "programmingLanguage":
            self._capture = "lang"
        elif tag == "span" and "float-sm-right" in cls:
            self._capture = "period"

    def handle_data(self, data):
        if self._capture and self._cur is not None:
            text = data.strip()
            if not text:
                return
            if self._capture == "desc":
                self._cur["desc"] += text + " "
            elif self._capture == "lang":
                self._cur["lang"] = text
            elif self._capture == "period":
                m = re.search(r"([\d,]+)", text)
                if m:
                    self._cur["period_stars"] = int(m.group(1).replace(",", ""))

    def handle_endtag(self, tag):
        if tag in ("p", "span"):
            self._capture = None
        if tag == "article" and self._cur is not None:
            if self._cur["slug"]:
                self.repos.append(self._cur)
            self._cur = None


class GitHubTrendingScraper(Scraper):
    name = "github"

    def __init__(self, limit=25):
        self.limit = limit

    def discover(self):
        req = urllib.request.Request(TRENDING_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        parser = _TrendingParser()
        parser.feed(html)

        items = []
        for r in parser.repos[: self.limit]:
            slug = r["slug"]
            owner = slug.split("/")[0].lower()
            name = slug.split("/")[-1]
            lang = (r["lang"] or "").lower()
            quadrant = _LANG_QUADRANT.get(lang, "Tools")
            # momentum: normalize period stars onto a 0-100 feel
            momentum = min(100, r["period_stars"] // 10)
            desc = r["desc"].strip() or f"A {lang or 'software'} project trending on GitHub."
            company = _KNOWN_COMPANIES.get(owner)  # None if not a known vendor
            items.append(new_item(
                source="GitHub",
                key=slug,
                name=name,
                description=desc,
                url=f"https://github.com/{slug}",
                quadrant=quadrant,
                momentum=momentum,
                stars=r["period_stars"],
                tags=[t for t in [lang] if t],
                company=company,
            ))
        return items


if __name__ == "__main__":
    for it in GitHubTrendingScraper(limit=5).discover():
        print(it["id"], "->", it["name"])
