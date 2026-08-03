"""
learning_core.py — shared library for the Learning Library.

Storage model: a single JSON document, data/learning.json, of the shape
  { "generated": "<date>", "items": [ {...}, {...} ] }

Unlike the tech radar (one file per technology, discovered by scrapers), the
Learning Library is small and entirely hand-curated, so it lives in one file.
This module is the read/write/validate layer the learning.py CLI sits on;
keeping it pure and separate mirrors how radar_core backs radar.py.

Every item carries a `type` (book · article · video · certification), a
consumption `status`, curated `topics`, and a `rating`. Type-specific
"length" fields differ (books: pages/pages_read, articles: minutes, videos:
duration, certifications: price) — new_item builds the right key set per type
so the web page (web/learning.jsx) renders each card correctly.
"""

import json
import os
import re
from datetime import date

# --- paths -------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
LEARNING_JSON = os.path.join(DATA_DIR, "learning.json")

# --- vocabulary --------------------------------------------------------
TYPES = ["book", "article", "video", "certification"]

# Consumption pipeline, ordered most-resolved first — the same convention
# the tech radar uses for rings (Adopted → … → Archived). Read sits innermost
# (done), Shelved furthest out (a deliberate "not now" set-aside).
STATUS_ORDER = ["Read", "Reading", "Queued", "Discovered", "Shelved"]

# The date field each status stamps when an item enters it. Mirrors how the
# radar stamps archived_at on entry to Archived: set on the way in (preserving
# an existing stamp), and `shelved` is cleared on the way back out.
STATUS_DATE_FIELD = {
    "Discovered": "added",
    "Queued": "queued",
    "Reading": "started",
    "Read": "finished",
    "Shelved": "shelved",
}

# Curated topic vocabulary — the SAME set the tech radar uses (minus the two
# scraper-only OCR/Data-Feeds extras the radar added), so a book and a
# technology can share a topic. Kept in sync with TOPICS in web/learning.jsx.
TOPICS = ["AI", "ML", "Agents", "Skills", "Prompts",
          "Trading", "Quant", "RAG", "Data Feeds"]

# The type-specific "length" field(s) each content type carries.
TYPE_LENGTH_FIELDS = {
    "book": ["pages", "pages_read"],
    "article": ["minutes"],
    "video": ["duration"],
    "certification": ["price"],
}


def normalize_topics(values):
    """Validate/canonicalize an iterable of topic strings against TOPICS.

    Case-insensitive ('agents' -> 'Agents'); order preserved, duplicates
    dropped. Returns (kept, unknown) so callers can report rejects. A falsy
    input yields ([], []). Identical contract to radar_core.normalize_topics."""
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


# --- id helpers --------------------------------------------------------
def slugify(text):
    """Human-readable id slug from a title, e.g. 'Team Topologies' ->
    'team-topologies'. Kept short and hyphenated to match existing ids."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return slug[:60] or "item"


def unique_id(base, existing_ids):
    """Return `base`, or base-2, base-3, … so it doesn't collide with an
    id already in the library."""
    if base not in existing_ids:
        return base
    n = 2
    while f"{base}-{n}" in existing_ids:
        n += 1
    return f"{base}-{n}"


# --- read / write ------------------------------------------------------
def load():
    """Load the whole document ({generated, items}). Returns a fresh empty
    document if the file doesn't exist yet."""
    if not os.path.exists(LEARNING_JSON):
        return {"generated": date.today().isoformat(), "items": []}
    with open(LEARNING_JSON, encoding="utf-8") as f:
        return json.load(f)


def load_items():
    """Just the items list."""
    return load().get("items", [])


def save(doc, day=None):
    """Persist the document, stamping `generated` with today's date so the
    dashboard's 'generated' line stays honest. Writing this file IS the
    publish step — the Learning Library page reads data/learning.json
    directly (there is no separate build like the radar's radar.json)."""
    doc["generated"] = day or date.today().isoformat()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LEARNING_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return len(doc.get("items", []))


def resolve(items, needle):
    """Find one item by exact id, exact title, or unique partial title
    (case-insensitive). Returns (item, None) on success or (None, message)
    describing the miss/ambiguity — the CLI turns that into an exit."""
    n = (needle or "").lower()
    for it in items:
        if it.get("id", "").lower() == n:
            return it, None
    exact = [it for it in items if it.get("title", "").lower() == n]
    if len(exact) == 1:
        return exact[0], None
    partial = [it for it in items if n in it.get("title", "").lower()]
    if len(partial) == 1:
        return partial[0], None
    if len(partial) > 1:
        names = ", ".join(p.get("title", p.get("id", "?")) for p in partial)
        return None, f"ambiguous '{needle}' — matches: {names}"
    return None, f"no item matches '{needle}'"


# --- the item schema ---------------------------------------------------
def new_item(item_type, title, author=None, topics=None, year=None,
             blurb=None, url=None, source=None, status="Discovered",
             pages=None, minutes=None, duration=None, price=None,
             existing_ids=None):
    """Build a fresh Learning Library item with the exact key set the web
    page expects for its type. Shared fields come first; type-specific
    length/url/source fields are added per TYPES. The status's date stamp
    (e.g. `added` for Discovered) is set to today."""
    if item_type not in TYPES:
        raise ValueError(f"type must be one of: {', '.join(TYPES)}")
    if status not in STATUS_ORDER:
        raise ValueError(f"status must be one of: {', '.join(STATUS_ORDER)}")
    kept, _ = normalize_topics(topics)
    base = slugify(title)
    item_id = unique_id(base, set(existing_ids or []))

    item = {
        "id": item_id,
        "type": item_type,
        "title": title,
        "author": author or "",
    }
    # articles, videos and certifications carry a source + url; books don't.
    if item_type != "book":
        item["source"] = source or ""
        item["url"] = url or ""
    # certifications list price right after source/url (matches existing data)
    if item_type == "certification":
        item["price"] = price
    item["year"] = int(year) if year not in (None, "") else None
    item["status"] = status
    item["topics"] = kept
    # type-specific length fields
    if item_type == "book":
        item["pages"] = int(pages) if pages not in (None, "") else None
        item["pages_read"] = None
    elif item_type == "article":
        item["minutes"] = int(minutes) if minutes not in (None, "") else None
    elif item_type == "video":
        item["duration"] = duration or None
    # shared consumption/metadata fields
    item["rating"] = None
    for f in ("added", "started", "queued", "finished", "shelved"):
        item[f] = None
    item[STATUS_DATE_FIELD[status]] = date.today().isoformat()
    item["blurb"] = blurb or ""
    return item


def set_status(item, status, day=None):
    """Move an item to a consumption status, stamping the matching date
    field (preserving an existing stamp) and clearing the `shelved` stamp +
    note when leaving Shelved — the mirror of radar_core clearing archived_at
    on the way out of Archived."""
    if status not in STATUS_ORDER:
        raise ValueError(f"status must be one of: {', '.join(STATUS_ORDER)}")
    today = day or date.today().isoformat()
    if item.get("status") == "Shelved" and status != "Shelved":
        item["shelved"] = None
        item.pop("shelved_note", None)
    field = STATUS_DATE_FIELD[status]
    if not item.get(field):
        item[field] = today
    item["status"] = status
    return item
