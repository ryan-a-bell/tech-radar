#!/usr/bin/env python3
"""
build_books.py — sync the Reading List (data/books.json) from a Calibre
library via Calibre's official `calibredb` CLI.

  python build_books.py                       # pull local library, rebuild books.json
  python build_books.py --library /path/lib   # explicit library folder
  python build_books.py --library http://host:8080/#Lib   # a Content Server
  python build_books.py --dry-run             # pull + report, write nothing

Design — who owns which field
-----------------------------
Calibre is the source of truth for the *factual* metadata of a book:

    title, author, year (pubdate), rating, blurb (comments), topics (tags),
    added (timestamp)

The *reading state* — status / pages_read / started / finished — has no native
Calibre field. Two sources fill it, in priority order:

  1. Calibre **custom columns** (`#status`, `#pages_read`, `#started`,
     `#finished`, `#pages`) when they exist in the library. Detected at runtime
     with `calibredb custom_columns`, so nothing breaks if you haven't made
     them.
  2. Otherwise the value already in data/books.json (the *overlay*) is kept,
     matched by title+author. This is what preserves hand-curated reading
     state and blurbs when Calibre has nothing to say.

A library book with no match in either source defaults to status "Discovered".
Books that live in books.json but are no longer in the Calibre library are kept
(so hand-added entries survive) and reported.

The pull (talking to Calibre — slow, does I/O) and the build (mapping + merge +
write — fast, pure) are deliberately separate entry points so a caller can run
them independently:

    records = fetch_calibre_books(library)      # or: await fetch_calibre_books_async(...)
    build_books_json(records=records)           # map + merge overlay + write

Output shape (data/books.json) — unchanged from the hand-curated format:
  { "generated": "2026-07-16",
    "books": [ { id, title, author, year, status, topics, pages, pages_read,
                 rating, added, started, finished, blurb } ] }
"""

import argparse
import asyncio
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

import radar_core

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "books.json")

# Base fields always requested from calibredb (all exist in every library).
BASE_FIELDS = ["id", "title", "authors", "pubdate", "rating", "comments",
               "tags", "timestamp"]

# books.json reading-state field  ->  Calibre custom-column label.
# Only the ones that actually exist in the library are requested/read.
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


def _match_key(title, author):
    """Stable key for matching a Calibre book to an overlay entry."""
    return f"{(title or '').strip().lower()}|{(author or '').strip().lower()}"


def _slug(title):
    """Fallback id for a book Calibre knows but the overlay doesn't."""
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return "-".join(s.split("-")[:6]) or "book"


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
    # each line looks like: "status (Status) [type: text]" — label is token 1
    labels = set()
    for line in out.splitlines():
        line = line.strip()
        if line:
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
    Synchronous. This is the slow, I/O-bound half of the sync."""
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
    the pull never blocks the event loop (or a concurrent site build)."""
    try:
        cols = await _run_async([calibredb, "custom_columns"] + _lib_args(library))
        available = {ln.split()[0] for ln in cols.splitlines() if ln.strip()}
    except (RuntimeError, FileNotFoundError) as e:
        print(f"  ! could not list custom columns: {e}", file=sys.stderr)
        available = set()
    out = await _run_async(_list_cmd(_fields_for(available), library, calibredb))
    return json.loads(out or "[]")


# --- mapping + merge (pure) -------------------------------------------
def calibre_to_book(raw):
    """Map one --for-machine record to a partial books.json entry. Only the
    fields Calibre actually knows are populated; reading state comes from the
    overlay unless custom columns supplied it."""
    title = (raw.get("title") or "").strip()
    author = (raw.get("authors") or "").strip()
    rating10 = raw.get("rating")
    tags, _bad = radar_core.normalize_topics(raw.get("tags") or [])

    book = {
        "title": title,
        "author": author,
        "year": _year(raw.get("pubdate")),
        "rating": (rating10 // 2) if isinstance(rating10, int) and rating10 else None,
        "topics": tags,
        "added": _date(raw.get("timestamp")),
        "blurb": strip_html(raw.get("comments")),
    }

    # reading state from custom columns, when present
    status = _get_custom(raw, CUSTOM_FIELDS["status"])
    if status:
        book["status"] = str(status).strip().title()
    for fld in ("pages_read", "pages", "started", "finished"):
        val = _get_custom(raw, CUSTOM_FIELDS[fld])
        if val not in (None, ""):
            book[fld] = _date(val) if fld in ("started", "finished") else val
    return book


def merge_books(calibre_books, overlay):
    """Overlay Calibre facts onto the existing curated list.

    For each Calibre book: start from the matching overlay entry (keeping its
    id, reading state, and any curated blurb/topics/pages), then let Calibre's
    non-empty facts win. Overlay-only books (not in the library) are kept and
    returned separately so the caller can report them."""
    by_key = {_match_key(b.get("title"), b.get("author")): b for b in overlay}
    matched_keys = set()
    out = []

    for raw in calibre_books:
        mapped = calibre_to_book(raw)
        key = _match_key(mapped["title"], mapped["author"])
        base = dict(by_key.get(key, {}))
        matched_keys.add(key)

        merged = {
            "id": base.get("id") or _slug(mapped["title"]),
            "title": mapped["title"] or base.get("title"),
            "author": mapped["author"] or base.get("author"),
            "year": mapped["year"] if mapped["year"] is not None else base.get("year"),
            "status": mapped.get("status") or base.get("status") or DEFAULT_STATUS,
            # topics: union of curated + Calibre tags, curated order first
            "topics": base.get("topics", []) + [t for t in mapped["topics"]
                                                 if t not in base.get("topics", [])],
            "pages": mapped.get("pages", base.get("pages")),
            "pages_read": mapped.get("pages_read", base.get("pages_read")),
            "rating": mapped["rating"] if mapped["rating"] is not None else base.get("rating"),
            "added": mapped["added"] or base.get("added"),
            "started": mapped.get("started", base.get("started")),
            "finished": mapped.get("finished", base.get("finished")),
            # curated blurb wins unless empty; then fall back to Calibre's
            "blurb": base.get("blurb") or mapped["blurb"] or "",
        }
        out.append(merged)

    orphans = [b for k, b in by_key.items() if k not in matched_keys]
    out.sort(key=lambda b: (b.get("title") or "").lower())
    return out, orphans


def load_overlay():
    if not os.path.exists(OUT):
        return []
    with open(OUT, encoding="utf-8") as f:
        return json.load(f).get("books", [])


def build_books_json(records=None, library=None, calibredb="calibredb",
                     keep_orphans=True, dry_run=False):
    """Map + merge + write data/books.json. If `records` is given (e.g. from an
    already-completed async pull) the Calibre fetch is skipped. Returns the
    list of book records written."""
    if records is None:
        records = fetch_calibre_books(library, calibredb)
    overlay = load_overlay()
    books, orphans = merge_books(records, overlay)

    if orphans:
        print(f"  {len(orphans)} book(s) in books.json not in the Calibre library "
              f"— kept" if keep_orphans else f"— dropped")
        for o in orphans:
            print(f"    · {o.get('title')} — {o.get('author')}")
    if keep_orphans:
        books = books + orphans
        books.sort(key=lambda b: (b.get("title") or "").lower())

    if dry_run:
        print(f"  dry run: {len(books)} book(s), nothing written")
        return books

    payload = {"generated": _dt.date.today().isoformat(), "books": books}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return books


def main():
    ap = argparse.ArgumentParser(description="Sync books.json from a Calibre library.")
    ap.add_argument("--library", help="library folder or Content Server URL "
                                       "(passed to calibredb --with-library)")
    ap.add_argument("--calibredb", default="calibredb", help="path to the calibredb binary")
    ap.add_argument("--drop-orphans", action="store_true",
                    help="drop books.json entries missing from the Calibre library")
    ap.add_argument("--dry-run", action="store_true", help="pull + report, write nothing")
    args = ap.parse_args()

    try:
        books = build_books_json(
            library=args.library, calibredb=args.calibredb,
            keep_orphans=not args.drop_orphans, dry_run=args.dry_run,
        )
    except FileNotFoundError:
        sys.exit(f"error: '{args.calibredb}' not found — is Calibre installed and on PATH?")
    except subprocess.CalledProcessError as e:
        sys.exit(f"error: calibredb failed: {e.stderr or e}")
    print(f"{'would build' if args.dry_run else 'built'} books.json ({len(books)} books)")


if __name__ == "__main__":
    main()
