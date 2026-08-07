#!/usr/bin/env python3
"""
calibre_sync.py — sync the Learning Library's *books* from a Calibre library,
via Calibre's official `calibredb` CLI.

  python calibre_sync.py                       # default local library
  python calibre_sync.py --library /path/lib   # explicit library folder
  python calibre_sync.py --library http://host:8080/#Lib   # a Content Server
  python calibre_sync.py --dry-run             # pull + report, write nothing

How it fits the Learning Library
--------------------------------
The source of truth is one Markdown file per item under learning/ (see
learning/README.md). This script does what the learning.py CLI does — write
`learning/<id>.md` and then refresh data/learning.json — but the field values
come from Calibre instead of a human. It only ever writes `type: book` items;
articles, videos, and certifications are never touched.

Who owns which field
---------------------
Calibre owns the *facts* of a book:

    title, author, year (pubdate), rating, pages, blurb (comments),
    topics (tags), added (timestamp)

The *reading state* — status / pages_read / started / finished — has no native
Calibre field, so it comes from Calibre **custom columns** (`#status`,
`#pages_read`, `#started`, `#finished`, `#pages`) when they exist, and is
otherwise **preserved from the existing learning/<id>.md**. This is what keeps
hand-curated status and blurbs from being clobbered. A library book with no
existing file is added as `Discovered`.

Books already in learning/ but no longer in the Calibre library are left
untouched and reported (never deleted).

Matching: a Calibre book is matched to an existing item by case-insensitive
title + author. If Calibre spells the author differently from the .md, the two
won't match — see the README note on reconciling author strings.

The pull (talking to Calibre — slow, I/O) and the write (map + merge + save —
fast, pure) are separate entry points so a caller can run them independently:

    records = fetch_calibre_books(library)        # or: await fetch_calibre_books_async(...)
    sync_books(records=records)                   # map + merge + write learning/*.md + refresh JSON
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

import learning_core as core
from build_learning import build_learning_json

# Base fields always requested from calibredb (present in every library).
BASE_FIELDS = ["id", "title", "authors", "pubdate", "rating", "comments",
               "tags", "timestamp"]

# learning field  ->  Calibre custom-column label. Only the columns that
# actually exist in the library are requested/read.
CUSTOM_FIELDS = {
    "status": "status",
    "pages_read": "pages_read",
    "started": "started",
    "finished": "finished",
    "pages": "pages",
}

DEFAULT_STATUS = "Discovered"


# --- small helpers -----------------------------------------------------
class _Stripper(HTMLParser):
    """Collapse a Calibre `comments` HTML blob down to plain text."""
    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data):
        self._chunks.append(data)

    def text(self):
        return re.sub(r"\s+", " ", "".join(self._chunks)).strip()


def strip_html(html):
    if not html:
        return ""
    p = _Stripper()
    p.feed(html)
    return p.text()


def _int(v):
    if v in (None, ""):
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _year(iso):
    """Year out of a Calibre ISO date, or None. Calibre uses year 101 for
    'undefined', so anything that old is treated as missing."""
    if not iso:
        return None
    m = re.match(r"(\d{3,4})-", str(iso))
    if not m:
        return None
    y = int(m.group(1))
    return y if y > 101 else None


def _date(iso):
    """YYYY-MM-DD out of a Calibre ISO datetime, or None."""
    if not iso:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(iso))
    if not m:
        return None
    return None if m.group(1).startswith("0101") else m.group(1)


def _get_custom(raw, label):
    """Read a custom-column value from a --for-machine record, tolerating the
    several key spellings calibredb has used (`#label`, `*label`, `label`)."""
    for key in (f"#{label}", f"*{label}", label):
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
    return None


def match_key(title, author):
    """Stable key for matching a Calibre book to an existing learning item."""
    return f"{(title or '').strip().lower()}|{(author or '').strip().lower()}"


# --- talking to calibredb ---------------------------------------------
def _lib_args(library):
    return ["--with-library", library] if library else []


def calibre_custom_columns(library=None, calibredb="calibredb"):
    """Return the set of custom-column labels defined in the library."""
    try:
        out = subprocess.run(
            [calibredb, "custom_columns"] + _lib_args(library),
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  ! could not list custom columns: {e}", file=sys.stderr)
        return set()
    labels = set()
    for line in out.splitlines():
        line = line.strip()
        if line:  # each line: "status (Status) [type: text]" -> label is token 1
            labels.add(line.split()[0])
    return labels


def _fields_for(available):
    """Base fields + whichever configured custom columns actually exist."""
    fields = list(BASE_FIELDS)
    for label in CUSTOM_FIELDS.values():
        if label in available:
            fields.append(f"#{label}")
    return fields


def _list_cmd(fields, library, calibredb):
    return ([calibredb, "list", "--for-machine", f"--fields={','.join(fields)}"]
            + _lib_args(library))


def fetch_calibre_books(library=None, calibredb="calibredb"):
    """Pull every book from the Calibre library as raw --for-machine records.
    Synchronous. The slow, I/O-bound half of the sync."""
    available = calibre_custom_columns(library, calibredb)
    cmd = _list_cmd(_fields_for(available), library, calibredb)
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out or "[]")


async def _run_async(cmd):
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"{cmd[0]} exited {proc.returncode}: {stderr.decode(errors='replace')}")
    return stdout.decode()


async def fetch_calibre_books_async(library=None, calibredb="calibredb"):
    """Async twin of fetch_calibre_books — awaits the calibredb subprocess so
    the pull never blocks the event loop (or a concurrent build)."""
    try:
        cols = await _run_async([calibredb, "custom_columns"] + _lib_args(library))
        available = {ln.split()[0] for ln in cols.splitlines() if ln.strip()}
    except (RuntimeError, FileNotFoundError) as e:
        print(f"  ! could not list custom columns: {e}", file=sys.stderr)
        available = set()
    out = await _run_async(_list_cmd(_fields_for(available), library, calibredb))
    return json.loads(out or "[]")


# --- mapping + merge (pure) -------------------------------------------
def calibre_facts(raw):
    """Extract the Calibre-owned facts (+ any reading-state custom columns)
    from one --for-machine record."""
    rating10 = raw.get("rating")
    topics, _bad = core.normalize_topics(raw.get("tags") or [])
    status = _get_custom(raw, CUSTOM_FIELDS["status"])
    return {
        "title": (raw.get("title") or "").strip(),
        "author": (raw.get("authors") or "").strip(),
        "year": _year(raw.get("pubdate")),
        "rating": (rating10 // 2) if isinstance(rating10, int) and rating10 else None,
        "pages": _int(_get_custom(raw, CUSTOM_FIELDS["pages"])),
        "topics": topics,
        "added": _date(raw.get("timestamp")),
        "blurb": strip_html(raw.get("comments")),
        # reading state — only from custom columns
        "status": str(status).strip().title() if status else None,
        "pages_read": _int(_get_custom(raw, CUSTOM_FIELDS["pages_read"])),
        "started": _date(_get_custom(raw, CUSTOM_FIELDS["started"])),
        "finished": _date(_get_custom(raw, CUSTOM_FIELDS["finished"])),
    }


def apply_to_existing(item, facts):
    """Overlay Calibre facts onto an existing book item *in place*, preserving
    the item's id, curated reading state, date stamps, and blurb. Facts win
    only where Calibre actually has a value."""
    if facts["title"]:
        item["title"] = facts["title"]
    if facts["author"]:
        item["author"] = facts["author"]
    if facts["year"] is not None:
        item["year"] = facts["year"]
    if facts["rating"] is not None:
        item["rating"] = facts["rating"]
    if facts["pages"] is not None:
        item["pages"] = facts["pages"]
    if facts["added"] and not item.get("added"):
        item["added"] = facts["added"]
    # topics: union, curated order first
    curated = item.get("topics", [])
    item["topics"] = curated + [t for t in facts["topics"] if t not in curated]
    # blurb: keep curated; fill only when empty
    if not (item.get("blurb") or "").strip() and facts["blurb"]:
        item["blurb"] = facts["blurb"]
    # reading state: custom columns win; otherwise leave the curated value.
    # Set status directly (no auto-stamp) — the started/finished stamps come
    # from Calibre's own custom columns below, not today's date.
    if facts["status"] in core.STATUS_ORDER:
        item["status"] = facts["status"]
    if facts["pages_read"] is not None:
        item["pages_read"] = facts["pages_read"]
    if facts["started"]:
        item["started"] = facts["started"]
    if facts["finished"]:
        item["finished"] = facts["finished"]
    return item


def new_book(facts, existing_ids):
    """Build a fresh `book` item from Calibre facts."""
    status = facts["status"] if facts["status"] in core.STATUS_ORDER else DEFAULT_STATUS
    item = core.new_item(
        item_type="book",
        title=facts["title"],
        author=facts["author"],
        topics=facts["topics"],
        year=facts["year"],
        blurb=facts["blurb"],
        status=status,
        pages=facts["pages"],
        existing_ids=existing_ids,
    )
    # facts new_item doesn't take directly
    if facts["rating"] is not None:
        item["rating"] = facts["rating"]
    if facts["pages_read"] is not None:
        item["pages_read"] = facts["pages_read"]
    if facts["added"]:          # override new_item's today-stamp for Discovered
        item["added"] = facts["added"]
    if facts["started"]:
        item["started"] = facts["started"]
    if facts["finished"]:
        item["finished"] = facts["finished"]
    return item


def plan_sync(records, items):
    """Pure planner: given Calibre records and the current learning items,
    return (added, updated, orphans). `updated`/`added` are the book items to
    write (existing items are mutated in place); `orphans` are existing book
    items not present in the Calibre library. Non-book items are ignored."""
    books = [it for it in items if it.get("type") == "book"]
    index = {match_key(b.get("title"), b.get("author")): b for b in books}
    existing_ids = {it.get("id") for it in items}

    added, updated, seen = [], [], set()
    for raw in records:
        facts = calibre_facts(raw)
        if not facts["title"]:
            continue
        key = match_key(facts["title"], facts["author"])
        seen.add(key)
        if key in index:
            updated.append(apply_to_existing(index[key], facts))
        else:
            item = new_book(facts, existing_ids)
            existing_ids.add(item["id"])
            index[key] = item
            added.append(item)

    orphans = [b for b in books if match_key(b.get("title"), b.get("author")) not in seen]
    return added, updated, orphans


def _report(added, updated, orphans):
    print(f"  {len(added)} new, {len(updated)} updated, {len(orphans)} in "
          f"learning/ but not in Calibre (kept)")
    for it in added:
        print(f"    + {it['title']} — {it['author']}  ({it['id']})")
    for it in orphans:
        print(f"    · orphan: {it['title']} — {it['author']}  ({it['id']})")


def sync_books(records=None, library=None, calibredb="calibredb", dry_run=False):
    """Map + merge + write. If `records` is given (e.g. from an already-completed
    async pull) the Calibre fetch is skipped. Writes each affected learning/<id>.md
    and refreshes data/learning.json. Returns (added, updated, orphans)."""
    if records is None:
        records = fetch_calibre_books(library, calibredb)
    items = core.load_items()
    added, updated, orphans = plan_sync(records, items)
    _report(added, updated, orphans)

    if dry_run:
        print("  dry run: nothing written")
        return added, updated, orphans

    for item in added + updated:
        core.save_item(item)
    n = build_learning_json()
    print(f"  ✓ learning/ + learning.json updated ({n} items total)")
    return added, updated, orphans


def main():
    ap = argparse.ArgumentParser(description="Sync Learning Library books from Calibre.")
    ap.add_argument("--library", help="library folder or Content Server URL "
                                       "(passed to calibredb --with-library)")
    ap.add_argument("--calibredb", default="calibredb", help="path to the calibredb binary")
    ap.add_argument("--dry-run", action="store_true", help="pull + report, write nothing")
    args = ap.parse_args()

    try:
        sync_books(library=args.library, calibredb=args.calibredb, dry_run=args.dry_run)
    except FileNotFoundError:
        sys.exit(f"error: '{args.calibredb}' not found — is Calibre installed and on PATH?")
    except subprocess.CalledProcessError as e:
        sys.exit(f"error: calibredb failed: {e.stderr or e}")


if __name__ == "__main__":
    main()
