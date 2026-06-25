#!/usr/bin/env python3
"""
radar.py — manage the technology radar without hand-editing JSON.

  python radar.py list                        # all items, grouped by ring
  python radar.py list --ring Discovered      # just the review queue
  python radar.py list --topic Agents         # items tagged with a topic
  python radar.py list --ring Archived --older-than 90   # stale archives
  python radar.py show <id-or-name>           # full detail for one item
  python radar.py promote <id-or-name> Trial  # move an item to a ring
  python radar.py demote <id-or-name>         # send back to Discovered
  python radar.py set <id-or-name> quadrant Platforms
  python radar.py set <id-or-name> company "Anthropic"
  python radar.py set <id-or-name> topics "AI,Agents"   # curated topics
  python radar.py archive <id-or-name>        # move to Archived (dated)
  python radar.py stale --days 30             # cold inbox items (archive candidates)
  python radar.py stale --days 30 --archive   # archive them after a y/N prompt
  python radar.py add "<name>" -q Tools -d "..." -u <url>  # manual add
  python radar.py find <text>                 # search name/description

After any change the dashboard's radar.json is rebuilt automatically.
Names are matched case-insensitively; partial matches work if unique.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radar_core as core  # noqa: E402

RING_ORDER = ["Adopted", "Trial", "Assess", "Discovered", "Archived"]


def _rebuild():
    """Refresh radar.json by deferring to the runner's builder."""
    from runner import build_radar_json
    n = build_radar_json()
    print(f"  ↻ radar.json rebuilt ({n} technologies)")


def _resolve(needle):
    """Find one item by exact id, exact name, or unique partial name."""
    items = core.load_all_items()
    n = needle.lower()
    # exact id
    for it in items:
        if it["id"].lower() == n:
            return it
    # exact name
    exact = [it for it in items if it["name"].lower() == n]
    if len(exact) == 1:
        return exact[0]
    # partial name
    partial = [it for it in items if n in it["name"].lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        print(f"  ambiguous '{needle}' — matches: "
              + ", ".join(p["name"] for p in partial))
        sys.exit(1)
    print(f"  no item matches '{needle}'")
    sys.exit(1)


def _write(item):
    """Persist a modified item back to its own file."""
    path = core.id_to_path(item["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(item, f, indent=2)


def _set_ring(item, ring):
    """Move an item to a ring, maintaining the archived_at stamp: set it on
    the way into Archived (preserving an existing stamp), clear it on the
    way out. Centralizes the one side effect a ring change carries."""
    from datetime import date
    if ring == "Archived":
        item["archived_at"] = item.get("archived_at") or date.today().isoformat()
    else:
        item["archived_at"] = None
    item["ring"] = ring


def cmd_list(args):
    items = core.load_all_items()
    if args.ring:
        items = [it for it in items if it["ring"] == args.ring]
    if args.topic:
        topic = args.topic.lower()
        items = [it for it in items
                 if topic in [t.lower() for t in it.get("topics", [])]]
    if args.older_than is not None:
        # only meaningful for archived items — keep those sat for N+ days.
        # days_since_archived is None for non-archived items (excluded) and
        # can be 0 (archived today), so test against None explicitly.
        def _old_enough(it):
            age = core.days_since_archived(it)
            return age is not None and age >= args.older_than
        items = [it for it in items if _old_enough(it)]
    by_ring = {r: [] for r in RING_ORDER}
    for it in items:
        by_ring.setdefault(it["ring"], []).append(it)
    for ring in RING_ORDER:
        group = by_ring.get(ring, [])
        if not group:
            continue
        print(f"\n[{ring}]  ({len(group)})")
        for it in sorted(group, key=lambda x: -x.get("momentum", 0)):
            co = f" · {it['company']}" if it.get("company") else ""
            tr = {"up": "▲", "down": "▼"}.get(it.get("trend"), " ")
            tp = f"  {{{', '.join(it['topics'])}}}" if it.get("topics") else ""
            age = core.days_since_archived(it)
            ag = f"  {age}d ago" if ring == "Archived" and age is not None else ""
            print(f"  {tr} {it['name']:<28} {it['quadrant']:<11} "
                  f"m{it.get('momentum', 0):<3}{co}{tp}{ag}")
    print()


def cmd_show(args):
    it = _resolve(args.item)
    print(json.dumps(it, indent=2))


def cmd_promote(args):
    if args.ring not in RING_ORDER:
        print(f"  ring must be one of: {', '.join(RING_ORDER)}")
        sys.exit(1)
    it = _resolve(args.item)
    old = it["ring"]
    _set_ring(it, args.ring)
    _write(it)
    print(f"  {it['name']}: {old} → {args.ring}")
    _rebuild()


def cmd_demote(args):
    it = _resolve(args.item)
    old = it["ring"]
    _set_ring(it, "Discovered")
    _write(it)
    print(f"  {it['name']}: {old} → Discovered")
    _rebuild()


def cmd_set(args):
    it = _resolve(args.item)
    field, value = args.field, args.value
    if field not in ("quadrant", "company", "description", "momentum", "topics"):
        print("  settable fields: quadrant, company, description, momentum, topics")
        sys.exit(1)
    if field == "quadrant" and value not in core.QUADRANTS:
        print(f"  quadrant must be one of: {', '.join(core.QUADRANTS)}")
        sys.exit(1)
    if field == "topics":
        # comma- or space-separated list, validated against the vocabulary
        raw = [t for t in re.split(r"[,\s]+", value) if t]
        kept, unknown = core.normalize_topics(raw)
        if unknown:
            print(f"  unknown topic(s): {', '.join(map(str, unknown))}")
            print(f"  valid topics: {', '.join(core.TOPICS)}")
            sys.exit(1)
        it["topics"] = kept
        _write(it)
        print(f"  {it['name']}: topics = {', '.join(kept) if kept else '(none)'}")
        _rebuild()
        return
    it[field] = int(value) if field == "momentum" else value
    _write(it)
    print(f"  {it['name']}: {field} = {value}")
    _rebuild()


def cmd_archive(args):
    it = _resolve(args.item)
    _set_ring(it, "Archived")
    _write(it)
    print(f"  {it['name']}: archived (Archived ring, {it['archived_at']})")
    _rebuild()


def cmd_add(args):
    """Manually add a technology. Marked discovered_by='manual'."""
    source = args.source or "Manual"
    key = args.key or _slugify_key(args.name)
    item = core.new_item(
        source=source,
        key=key,
        name=args.name,
        description=args.description or "",
        url=args.url or "",
        quadrant=args.quadrant or "Tools",
        momentum=args.momentum or 0,
        company=args.company,
        discovered_by="manual",
    )
    if core.save_new(item):
        print(f"  added {item['name']} — {item['id']} (manual)")
        _rebuild()
    else:
        print(f"  already exists: {item['id']} — nothing written")


def _slugify_key(text):
    import re
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "item"


def cmd_stale(args):
    """Surface inbox items that have gone cold — discovered once (or long
    ago) and not seen by any scraper in --days days. These are prime
    archive candidates. With --archive, archive them after confirmation.

    Only Discovered items are considered stale: once a human has curated
    an item into a ring, 'not trending anymore' is a different judgement
    that shouldn't be auto-archived."""
    items = [it for it in core.load_all_items()
             if it["ring"] == "Discovered"
             and core.days_since_seen(it) >= args.days]
    # coldest-but-least-interesting first: oldest sighting, lowest momentum
    items.sort(key=lambda it: (-core.days_since_seen(it), it.get("momentum", 0)))

    if not items:
        print(f"  no Discovered items cold for {args.days}+ days")
        return

    print(f"\n[stale]  {len(items)} Discovered item(s) not seen in {args.days}+ days\n")
    for it in items:
        age = core.days_since_seen(it)
        co = f" · {it['company']}" if it.get("company") else ""
        print(f"  {age:>4}d  {it['name']:<28} {it['quadrant']:<11} "
              f"m{it.get('momentum', 0):<3}{co}")
    print()

    if not args.archive:
        print("  re-run with --archive to archive these (Archived ring, dated)")
        return

    resp = input(f"  archive all {len(items)} item(s)? [y/N] ").strip().lower()
    if resp != "y":
        print("  aborted — nothing changed")
        return
    for it in items:
        _set_ring(it, "Archived")
        _write(it)
    print(f"  archived {len(items)} item(s)")
    _rebuild()


def cmd_find(args):
    n = args.text.lower()
    hits = [it for it in core.load_all_items()
            if n in it["name"].lower() or n in it.get("description", "").lower()]
    if not hits:
        print(f"  nothing matches '{args.text}'")
        return
    for it in hits:
        print(f"  [{it['ring']}] {it['name']} — {it['id']}")


def main():
    # restore default SIGPIPE so piping into head/less doesn't traceback
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass  # not available on Windows / non-main thread

    ap = argparse.ArgumentParser(description="manage the technology radar")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list items grouped by ring")
    p.add_argument("--ring", choices=RING_ORDER)
    p.add_argument("--topic", choices=core.TOPICS,
                   help="only items carrying this topic")
    p.add_argument("--older-than", type=int, metavar="DAYS",
                   help="only archived items sat this many+ days "
                        "(pair with --ring Archived)")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show full detail for one item")
    p.add_argument("item")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("promote", help="move an item to a ring")
    p.add_argument("item")
    p.add_argument("ring")
    p.set_defaults(func=cmd_promote)

    p = sub.add_parser("demote", help="send an item back to Discovered")
    p.add_argument("item")
    p.set_defaults(func=cmd_demote)

    p = sub.add_parser("set",
                       help="set a field (quadrant|company|description|"
                            "momentum|topics) on an item")
    p.add_argument("item")
    p.add_argument("field")
    p.add_argument("value", help="for topics: comma/space-separated, "
                                 "e.g. \"AI,Agents\"")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("archive", help="archive an item (Archived ring, dated)")
    p.add_argument("item")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("add", help="manually add a technology (discovered_by=manual)")
    p.add_argument("name")
    p.add_argument("--description", "-d")
    p.add_argument("--url", "-u")
    p.add_argument("--quadrant", "-q", choices=core.QUADRANTS)
    p.add_argument("--source", "-s", help="source label (default: Manual)")
    p.add_argument("--key", "-k", help="unique key (default: slug of name)")
    p.add_argument("--company", "-c")
    p.add_argument("--momentum", "-m", type=int)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("stale", help="list cold inbox items (archive candidates)")
    p.add_argument("--days", type=int, default=30,
                   help="not seen in this many days (default: 30)")
    p.add_argument("--archive", action="store_true",
                   help="archive the listed items after confirmation")
    p.set_defaults(func=cmd_stale)

    p = sub.add_parser("find", help="search name/description")
    p.add_argument("text")
    p.set_defaults(func=cmd_find)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
