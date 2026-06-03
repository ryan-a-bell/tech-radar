#!/usr/bin/env python3
"""
radar.py — manage the technology radar without hand-editing JSON.

  python radar.py list                        # all items, grouped by ring
  python radar.py list --ring Discovered      # just the review queue
  python radar.py show <id-or-name>           # full detail for one item
  python radar.py promote <id-or-name> Trial  # move an item to a ring
  python radar.py demote <id-or-name>         # send back to Discovered
  python radar.py set <id-or-name> quadrant Platforms
  python radar.py set <id-or-name> company "Anthropic"
  python radar.py archive <id-or-name>        # mark Hold + tag 'archived'
  python radar.py find <text>                 # search name/description

After any change the dashboard's radar.json is rebuilt automatically.
Names are matched case-insensitively; partial matches work if unique.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radar_core as core  # noqa: E402

RING_ORDER = ["Adopt", "Trial", "Assess", "Hold", "Discovered"]


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
    with open(path, "w") as f:
        json.dump(item, f, indent=2)


def cmd_list(args):
    items = core.load_all_items()
    if args.ring:
        items = [it for it in items if it["ring"] == args.ring]
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
            print(f"  {tr} {it['name']:<28} {it['quadrant']:<11} "
                  f"m{it.get('momentum', 0):<3}{co}")
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
    it["ring"] = args.ring
    _write(it)
    print(f"  {it['name']}: {old} → {args.ring}")
    _rebuild()


def cmd_demote(args):
    it = _resolve(args.item)
    old = it["ring"]
    it["ring"] = "Discovered"
    _write(it)
    print(f"  {it['name']}: {old} → Discovered")
    _rebuild()


def cmd_set(args):
    it = _resolve(args.item)
    field, value = args.field, args.value
    if field not in ("quadrant", "company", "description", "momentum"):
        print("  settable fields: quadrant, company, description, momentum")
        sys.exit(1)
    if field == "quadrant" and value not in core.QUADRANTS:
        print(f"  quadrant must be one of: {', '.join(core.QUADRANTS)}")
        sys.exit(1)
    it[field] = int(value) if field == "momentum" else value
    _write(it)
    print(f"  {it['name']}: {field} = {value}")
    _rebuild()


def cmd_archive(args):
    it = _resolve(args.item)
    it["ring"] = "Hold"
    if "archived" not in it.get("tags", []):
        it.setdefault("tags", []).append("archived")
    _write(it)
    print(f"  {it['name']}: archived (Hold + 'archived' tag)")
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
    ap = argparse.ArgumentParser(description="manage the technology radar")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list items grouped by ring")
    p.add_argument("--ring", choices=RING_ORDER)
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

    p = sub.add_parser("set", help="set a field on an item")
    p.add_argument("item")
    p.add_argument("field")
    p.add_argument("value")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("archive", help="archive an item (Hold + tag)")
    p.add_argument("item")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("find", help="search name/description")
    p.add_argument("text")
    p.set_defaults(func=cmd_find)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
