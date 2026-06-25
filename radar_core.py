"""
radar_core.py — shared library for the technology radar.

Storage model (Option 2): one plaintext JSON file per technology.
  data/items/<source>/<slug>.json

The `ring` field inside each file decides where it shows up. The runner
only ever writes ring="Discovered". A human edits the file to promote it.
Dedup = "does the file already exist?" — O(1), no parsing, no scan.
"""

import json
import os
import re
from datetime import date

# --- paths -------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
ITEMS_DIR = os.path.join(DATA_DIR, "items")
RAW_DIR = os.path.join(DATA_DIR, "raw")
RADAR_JSON = os.path.join(DATA_DIR, "radar.json")  # generated for the dashboard

QUADRANTS = ["Techniques", "Tools", "Platforms", "Languages"]
RINGS = ["Discovered", "Assess", "Trial", "Adopted", "Archived"]

# Curated topic vocabulary. Distinct from the free-form `tags` field that
# scrapers populate — `topics` is a controlled set a human assigns for
# cross-quadrant filtering (an Agents tool and an Agents technique share a
# topic but not a quadrant). Extend by adding to this list; unknown topics
# are rejected by normalize_topics so the vocabulary stays clean.
TOPICS = ["AI", "ML", "Agents", "Skills", "Prompts", "Trading", "Quant", "RAG"]


def normalize_topics(values):
    """Validate/canonicalize an iterable of topic strings against TOPICS.

    Matching is case-insensitive ('agents' -> 'Agents'); order is preserved
    and duplicates dropped. Returns (kept, unknown) so callers can report
    rejects. A falsy input yields ([], [])."""
    if not values:
        return [], []
    by_lower = {t.lower(): t for t in TOPICS}
    kept, unknown, seen = [], [], set()
    for v in values:
        canon = by_lower.get(str(v).strip().lower())
        if canon is None:
            unknown.append(v)
        elif canon not in seen:
            seen.add(canon)
            kept.append(canon)
    return kept, unknown


# --- id + slug helpers -------------------------------------------------
def make_id(source, key):
    """Stable, source-prefixed id. e.g. github:oven-sh/bun"""
    return f"{source.lower()}:{key}"


def _slugify(text):
    text = re.sub(r"[^a-zA-Z0-9]+", "__", text).strip("_")
    return text.lower()[:120]


def id_to_path(item_id):
    """Map an id to its file path. github:oven-sh/bun ->
    data/items/github/oven-sh__bun.json"""
    source, _, key = item_id.partition(":")
    return os.path.join(ITEMS_DIR, _slugify(source), _slugify(key) + ".json")


def exists(item_id):
    """The entire dedup check. No file is read."""
    return os.path.exists(id_to_path(item_id))


# --- canonical url extraction (cross-source dedup, Approach A) ---------
# Many discoveries point at the same GitHub repo from different sources
# (a Reddit post, a YouTube video, the repo itself). If we can reduce a
# url to a canonical repo, items sharing that canonical merge into one.
_GITHUB_RE = re.compile(
    r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)


def canonical_url(*urls):
    """Return a canonical identifier for a technology, or None.

    Currently recognizes GitHub repos — the highest-confidence signal.
    Pass any number of candidate urls (item url, linked url, etc.);
    the first that resolves to a repo wins. Trailing .git and paths
    like /tree/main are stripped so variants collapse together.
    """
    for u in urls:
        if not u:
            continue
        m = _GITHUB_RE.search(u)
        if m:
            owner, repo = m.group(1), m.group(2)
            repo = re.sub(r"\.git$", "", repo, flags=re.I)
            # ignore non-repo paths that look like owner/repo
            if repo.lower() in ("sponsors", "orgs", "settings", "topics"):
                continue
            return f"github.com/{owner.lower()}/{repo.lower()}"
    return None


# --- the item schema ---------------------------------------------------
def new_item(source, key, name, description, url,
             quadrant="Tools", momentum=0, stars=0, tags=None,
             company=None, linked_url=None, discovered_by="scraper",
             topics=None):
    """Build a fresh discovered item. The runner ALWAYS sets ring=Discovered.

    company: the org/vendor behind the tech, if it's a company product
             (e.g. "Anthropic", "Vercel"). None for community / individual
             projects. A scraper sets this when it can infer it.
    linked_url: a secondary url the source points at (e.g. the GitHub repo
             a Reddit post links to). Used for cross-source dedup — the
             scraper passes it when the source exposes one.
    discovered_by: provenance of this discovery. One of:
             "scraper" — found by an automated runner.py scraper (default)
             "llm"     — found by the weekly LLM organic-discovery routine
             "manual"  — added by a human
    """
    today = date.today().isoformat()
    return {
        "id": make_id(source, key),
        "name": name,
        "description": (description or "").strip(),
        "quadrant": quadrant if quadrant in QUADRANTS else "Tools",
        "ring": "Discovered",          # human changes this later
        "source": source,
        # how this tech entered the radar: scraper | llm | manual
        "discovered_by": discovered_by,
        "url": url,
        # canonical identity for cross-source merging — None if unknown
        "canonical_url": canonical_url(url, linked_url),
        # other (source, url) pairs this tech was also discovered at,
        # filled by the runner when it merges duplicates
        "also_seen": [],
        "company": company,            # vendor name, or None if community
        "stars": int(stars or 0),
        "momentum": int(momentum or 0),
        "tags": tags or [],            # free-form labels from the scraper
        # curated topic vocabulary (see TOPICS) — human-assigned, validated
        "topics": normalize_topics(topics)[0],
        # date this item entered the Archived ring; None while it's live.
        # Lets the dashboard/CLI filter the graveyard by how long it's sat.
        "archived_at": None,
        "first_seen": today,           # never changes after creation
        "last_seen": today,            # refreshed every scrape
        # star history: {date: star_count} — only filled for GitHub items.
        # the runner appends to this each run so the dashboard can show trend.
        "stars_history": {today: int(stars or 0)} if stars else {},
    }


# --- read / write ------------------------------------------------------
def save_new(item):
    """Write a NEW item. Returns True if written, False if it already
    existed (caller should treat False as 'skipped — known')."""
    path = id_to_path(item["id"])
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(item, f, indent=2)
    return True


def touch_last_seen(item_id, day=None, stars=None):
    """Refresh last_seen on an item we re-encountered, and optionally
    append today's star count to its history (GitHub items only).
    Leaves the human-owned fields (ring, quadrant, company) untouched."""
    path = id_to_path(item_id)
    if not os.path.exists(path):
        return False
    today = day or date.today().isoformat()
    with open(path, encoding="utf-8") as f:
        item = json.load(f)
    item["last_seen"] = today
    if stars is not None:
        item.setdefault("stars_history", {})[today] = int(stars)
        item["stars"] = int(stars)          # keep current count fresh
        # keep history bounded — last 90 snapshots is plenty
        if len(item["stars_history"]) > 90:
            keep = dict(sorted(item["stars_history"].items())[-90:])
            item["stars_history"] = keep
    with open(path, "w", encoding="utf-8") as f:
        json.dump(item, f, indent=2)
    return True


def star_trend(item):
    """Return ('up'|'down'|'flat', delta) from an item's star history.
    Compares newest snapshot against the one ~7+ days older. Returns
    ('none', 0) when there isn't enough history (e.g. non-GitHub items)."""
    hist = item.get("stars_history") or {}
    if len(hist) < 2:
        return ("none", 0)
    dates = sorted(hist)
    newest = dates[-1]
    # find the oldest snapshot at least 7 days before newest, else the oldest
    from datetime import date as _d
    nd = _d.fromisoformat(newest)
    baseline = dates[0]
    for dt in dates:
        if (nd - _d.fromisoformat(dt)).days >= 7:
            baseline = dt
    delta = hist[newest] - hist[baseline]
    if delta > 0:
        return ("up", delta)
    if delta < 0:
        return ("down", delta)
    return ("flat", 0)


def days_since_seen(item, today=None):
    """How many days since this tech was last discovered/seen by a scraper.
    Used to surface stale inbox items that never panned out. Returns a
    large number if last_seen is missing or unparseable (treat as stale)."""
    from datetime import date as _d
    today = today or _d.today()
    try:
        return (today - _d.fromisoformat(item["last_seen"])).days
    except (KeyError, ValueError, TypeError):
        return 10**6


def days_since_archived(item, today=None):
    """How many days an item has sat in the Archived ring. Returns None if
    it isn't archived or has no archived_at stamp — callers filtering the
    graveyard by age should skip those."""
    from datetime import date as _d
    stamp = item.get("archived_at")
    if not stamp:
        return None
    today = today or _d.today()
    try:
        return (today - _d.fromisoformat(stamp)).days
    except (ValueError, TypeError):
        return None


def load_all_items():
    """Walk the items tree and return every technology as a list."""
    out = []
    if not os.path.isdir(ITEMS_DIR):
        return out
    for root, _, files in os.walk(ITEMS_DIR):
        for fn in files:
            if fn.endswith(".json"):
                with open(os.path.join(root, fn), encoding="utf-8") as f:
                    out.append(json.load(f))
    return out


# --- cross-source dedup (Approach A) -----------------------------------
def canonical_index():
    """Return {canonical_url: item_id} for every stored item that has a
    canonical_url. Lets a scraper's find ask 'do we already know this
    tech under a *different* source?' before creating a duplicate."""
    idx = {}
    for it in load_all_items():
        cu = it.get("canonical_url")
        if cu:
            idx[cu] = it["id"]   # last writer wins; collisions are the same tech
    return idx


def record_also_seen(item_id, source, url, day=None):
    """Note that an already-known tech was re-discovered via another
    source. Appends to its `also_seen` list (deduped) and refreshes
    last_seen. Human-owned fields stay untouched. Returns True if this
    was a genuinely new sighting, False if already recorded."""
    path = id_to_path(item_id)
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        item = json.load(f)
    item["last_seen"] = day or date.today().isoformat()
    seen = item.setdefault("also_seen", [])
    # don't record the source the item already primarily belongs to
    if source == item.get("source"):
        return False
    for entry in seen:
        if entry.get("source") == source and entry.get("url") == url:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(item, f, indent=2)
            return False
    seen.append({"source": source, "url": url,
                 "seen": day or date.today().isoformat()})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(item, f, indent=2)
    return True
