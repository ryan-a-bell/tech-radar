#!/usr/bin/env python3
"""
learning.py — manage the Learning Library without hand-editing JSON.

  python learning.py list                          # all items, by status
  python learning.py list --status Reading         # just what's in progress
  python learning.py list --type certification     # only certifications
  python learning.py list --topic Quant            # items carrying a topic
  python learning.py show <id-or-title>            # full detail for one item
  python learning.py find <text>                   # search title/author/blurb
  python learning.py status <id-or-title> Reading  # move along the pipeline
  python learning.py set <id-or-title> rating 5    # set a field
  python learning.py set <id-or-title> pages_read 210
  python learning.py rate <id-or-title> 4          # shortcut for set … rating
  python learning.py shelve <id-or-title> --note "..."   # Shelved + why
  python learning.py add "<title>" --type book --author "..." \
      --topics "ML,AI" --blurb "..."               # add an entry
  python learning.py add "RAMS" --type conference --author "IEEE" \
      --url "..." --blurb "..."                     # add a recurring conference
  python learning.py edition RAMS --year 2026 \
      --dates "2026-01-19..01-22" --location "..." --status Registered
                                                    # track one year's occurrence

Status pipeline (most-resolved first, mirrors the radar's rings):
  Read → Reading → Queued → Discovered → Shelved
Moving into a status stamps its date (added/queued/started/finished/shelved).

Storage is one Markdown file per item under learning/ (the source of truth,
like people/ and projects/). Every command writes the affected .md files and
then refreshes the generated data/learning.json the web page reads, so a CLI
edit still publishes immediately. Hand-edit a .md instead? Run
`python build_learning.py` to republish.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import learning_core as core  # noqa: E402
from build_learning import build_learning_json  # noqa: E402

# Fields a human may set directly. Integer fields are coerced; `topics` is
# validated against the vocabulary; `rating` is bounded 1–5.
_INT_FIELDS = {"rating", "pages", "pages_read", "minutes", "year"}
_SETTABLE = (_INT_FIELDS | {
    "topics", "duration", "price", "blurb", "author", "source", "url",
    "title", "shelved_note", "recurrence",
})

# type-specific length labels for the list view
def _length(it):
    t = it.get("type")
    if t == "book":
        return f"{it['pages']}p" if it.get("pages") else ""
    if t == "article":
        return f"{it['minutes']}min" if it.get("minutes") else ""
    if t == "video":
        return it.get("duration") or ""
    if t == "certification":
        return it.get("price") or ""
    if t == "conference":
        ed = core.next_edition(it)
        if not ed:
            return ""
        when = ed.get("dates") or (str(ed["year"]) if ed.get("year") else "")
        where = ed.get("location") or ""
        return " · ".join(p for p in (when, where) if p)
    return ""


def _resolve_or_exit(items, needle):
    it, err = core.resolve(items, needle)
    if err:
        print(f"  {err}")
        sys.exit(1)
    return it


def _saved(doc):
    n = core.save(doc)                 # write the source-of-truth Markdown
    build_learning_json()              # refresh the generated data/learning.json
    print(f"  ✓ learning/ + learning.json updated ({n} items)")


def cmd_list(args):
    items = core.load_items()
    if args.status:
        items = [it for it in items if it.get("status") == args.status]
    if args.type:
        items = [it for it in items if it.get("type") == args.type]
    if args.topic:
        topic = args.topic.lower()
        items = [it for it in items
                 if topic in [t.lower() for t in it.get("topics", [])]]
    by_status = {s: [] for s in core.STATUS_ORDER}
    for it in items:
        by_status.setdefault(it.get("status", "Discovered"), []).append(it)
    icon = {"book": "▣", "article": "❡", "video": "▶", "certification": "⬡",
            "conference": "◈"}
    for status in core.STATUS_ORDER:
        group = by_status.get(status, [])
        if not group:
            continue
        print(f"\n[{status}]  ({len(group)})")
        for it in sorted(group, key=lambda x: x.get("title", "").lower()):
            gl = icon.get(it.get("type"), " ")
            rt = ("★" * it["rating"]) if it.get("rating") else ""
            tp = f"  {{{', '.join(it['topics'])}}}" if it.get("topics") else ""
            ln = _length(it)
            ln = f"  {ln}" if ln else ""
            title = it.get("title", "")
            title = title if len(title) <= 46 else title[:45] + "…"
            print(f"  {gl} {title:<46}{ln:<10}{rt:<6}{tp}")
    print()


def cmd_show(args):
    it = _resolve_or_exit(core.load_items(), args.item)
    print(json.dumps(it, indent=2, ensure_ascii=False))


def cmd_find(args):
    n = args.text.lower()
    hits = [it for it in core.load_items()
            if n in it.get("title", "").lower()
            or n in it.get("author", "").lower()
            or n in it.get("blurb", "").lower()]
    if not hits:
        print(f"  nothing matches '{args.text}'")
        return
    for it in hits:
        print(f"  [{it.get('status')}] {it.get('title')} "
              f"({it.get('type')}) — {it.get('id')}")


def cmd_status(args):
    if args.status not in core.STATUS_ORDER:
        print(f"  status must be one of: {', '.join(core.STATUS_ORDER)}")
        sys.exit(1)
    doc = core.load()
    it = _resolve_or_exit(doc["items"], args.item)
    old = it.get("status")
    core.set_status(it, args.status)
    print(f"  {it['title']}: {old} → {args.status}")
    _saved(doc)


def cmd_set(args):
    field, value = args.field, args.value
    if field not in _SETTABLE:
        print(f"  settable fields: {', '.join(sorted(_SETTABLE))}")
        sys.exit(1)
    doc = core.load()
    it = _resolve_or_exit(doc["items"], args.item)
    if field == "topics":
        raw = [t.strip() for t in value.split(",") if t.strip()]
        kept, unknown = core.normalize_topics(raw)
        if unknown:
            print(f"  unknown topic(s): {', '.join(map(str, unknown))}")
            print(f"  valid topics: {', '.join(core.TOPICS)}")
            sys.exit(1)
        it["topics"] = kept
        print(f"  {it['title']}: topics = {', '.join(kept) if kept else '(none)'}")
        _saved(doc)
        return
    if field in _INT_FIELDS:
        try:
            ivalue = int(value)
        except ValueError:
            print(f"  {field} must be an integer")
            sys.exit(1)
        if field == "rating" and not (1 <= ivalue <= 5):
            print("  rating must be between 1 and 5")
            sys.exit(1)
        it[field] = ivalue
    else:
        it[field] = value
    print(f"  {it['title']}: {field} = {it[field]}")
    _saved(doc)


def cmd_rate(args):
    if not (1 <= args.rating <= 5):
        print("  rating must be between 1 and 5")
        sys.exit(1)
    doc = core.load()
    it = _resolve_or_exit(doc["items"], args.item)
    it["rating"] = args.rating
    print(f"  {it['title']}: rating = {'★' * args.rating}")
    _saved(doc)


def cmd_shelve(args):
    doc = core.load()
    it = _resolve_or_exit(doc["items"], args.item)
    old = it.get("status")
    core.set_status(it, "Shelved")
    if args.note:
        it["shelved_note"] = args.note
    note = f' — "{args.note}"' if args.note else ""
    print(f"  {it['title']}: {old} → Shelved{note}")
    _saved(doc)


def cmd_add(args):
    doc = core.load()
    existing = {it.get("id") for it in doc["items"]}
    if args.topics:
        raw = [t.strip() for t in args.topics.split(",") if t.strip()]
        kept, unknown = core.normalize_topics(raw)
        if unknown:
            print(f"  unknown topic(s): {', '.join(map(str, unknown))}")
            print(f"  valid topics: {', '.join(core.TOPICS)}")
            sys.exit(1)
    else:
        kept = []
    try:
        item = core.new_item(
            item_type=args.type,
            title=args.title,
            author=args.author,
            topics=kept,
            year=args.year,
            blurb=args.blurb,
            url=args.url,
            source=args.source,
            status=args.status or "Discovered",
            pages=args.pages,
            minutes=args.minutes,
            duration=args.duration,
            price=args.price,
            recurrence=args.recurrence,
            existing_ids=existing,
        )
    except ValueError as e:
        print(f"  {e}")
        sys.exit(1)
    doc["items"].append(item)
    print(f"  added {item['title']} — {item['id']} "
          f"({item['type']}, {item['status']})")
    _saved(doc)


def cmd_edition(args):
    doc = core.load()
    it = _resolve_or_exit(doc["items"], args.item)
    if it.get("type") != "conference":
        print(f"  '{it['title']}' is a {it['type']}, not a conference — "
              "editions only apply to conferences")
        sys.exit(1)
    try:
        ed = core.upsert_edition(
            it, args.year, dates=args.dates, location=args.location,
            status=args.status, cfp=args.cfp, url=args.url)
    except ValueError as e:
        print(f"  {e}")
        sys.exit(1)
    where = f" — {ed['location']}" if ed.get("location") else ""
    print(f"  {it['title']}: {ed['year']} edition [{ed.get('status')}]{where}")
    _saved(doc)


def main():
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass  # not available on Windows / non-main thread

    ap = argparse.ArgumentParser(description="manage the Learning Library")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list items grouped by status")
    p.add_argument("--status", choices=core.STATUS_ORDER)
    p.add_argument("--type", choices=core.TYPES)
    p.add_argument("--topic", choices=core.TOPICS)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show full detail for one item")
    p.add_argument("item")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("find", help="search title/author/blurb")
    p.add_argument("text")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("status", help="move an item to a consumption status")
    p.add_argument("item")
    p.add_argument("status", help=" | ".join(core.STATUS_ORDER))
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("set", help="set a field on an item")
    p.add_argument("item")
    p.add_argument("field")
    p.add_argument("value", help="for topics: comma-separated, e.g. \"ML,AI\"")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("rate", help="set an item's 1-5 rating")
    p.add_argument("item")
    p.add_argument("rating", type=int)
    p.set_defaults(func=cmd_rate)

    p = sub.add_parser("shelve", help="shelve an item (Shelved + optional note)")
    p.add_argument("item")
    p.add_argument("--note", "-n", help="why it's being set aside for now")
    p.set_defaults(func=cmd_shelve)

    p = sub.add_parser("add", help="add a learning item")
    p.add_argument("title")
    p.add_argument("--type", "-t", required=True, choices=core.TYPES)
    p.add_argument("--author", "-a")
    p.add_argument("--topics", help="comma-separated, e.g. \"ML,AI\"")
    p.add_argument("--blurb", "-b")
    p.add_argument("--url", "-u")
    p.add_argument("--source", "-s",
                   help="publication/channel, or exam code for certifications")
    p.add_argument("--year", "-y", type=int)
    p.add_argument("--status", choices=core.STATUS_ORDER,
                   help="default: Discovered")
    p.add_argument("--pages", type=int, help="books")
    p.add_argument("--minutes", type=int, help="articles (read time)")
    p.add_argument("--duration", help="videos (e.g. \"1h 56m\")")
    p.add_argument("--price", help="certifications (exam fee, e.g. \"$150\")")
    p.add_argument("--recurrence",
                   help="conferences (cadence, e.g. \"annual\"; default annual)")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("edition",
                       help="add/update a conference's edition for a year")
    p.add_argument("item")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--dates", help="e.g. \"2026-06-13..06-18\" or \"13–18 Jun 2026\"")
    p.add_argument("--location", "--loc", dest="location",
                   help="host city / venue, e.g. \"Yokohama, Japan\"")
    p.add_argument("--status", choices=core.EDITION_STATUS,
                   help="default Announced for a new edition; unchanged otherwise")
    p.add_argument("--cfp", help="call-for-papers / abstract deadline")
    p.add_argument("--url", help="edition-specific page (optional)")
    p.set_defaults(func=cmd_edition)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
