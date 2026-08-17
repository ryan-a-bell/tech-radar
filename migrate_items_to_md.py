#!/usr/bin/env python3
"""
migrate_items_to_md.py — one-time migration: data/items/**/*.json -> *.md

Converts every per-technology JSON file to the new Markdown + YAML
frontmatter format (radar_core.dump_item_md), verifies the conversion is
lossless field-for-field (accounting for type-correct defaults on fields
older items may predate — see radar_core._FIELD_DEFAULTS), then removes the
old .json file. Aborts before deleting anything if any file fails to verify.

  python migrate_items_to_md.py            # convert + verify + delete .json
  python migrate_items_to_md.py --dry-run  # convert + verify only

Safe to re-run: an item that already has a .md file (and no .json) is
skipped.
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radar_core as core  # noqa: E402


def _expected(orig):
    """orig JSON dict, backfilled with the same type-correct defaults the
    frontmatter codec applies to fields absent from older schema versions."""
    expected = dict(orig)
    for key, default in core._FIELD_DEFAULTS.items():
        expected.setdefault(key, default)
    return expected


def migrate(dry_run=False):
    json_files = sorted(glob.glob(os.path.join(core.ITEMS_DIR, "**", "*.json"),
                                   recursive=True))
    if not json_files:
        print("no .json items found — nothing to migrate")
        return 0

    converted = []  # (json_path, md_path, item)
    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            orig = json.load(f)
        text = core.dump_item_md(orig)
        back = core.parse_item_md(text)
        expected = _expected(orig)
        if back != expected:
            keys = set(expected) | set(back)
            diffs = [(k, expected.get(k), back.get(k)) for k in keys
                     if expected.get(k) != back.get(k)]
            print(f"  ! round-trip mismatch, aborting: {jf}\n    {diffs}")
            return 1
        md_path = os.path.splitext(jf)[0] + ".md"
        converted.append((jf, md_path, text))

    print(f"  {len(converted)} item(s) verified lossless")
    if dry_run:
        print("  --dry-run: nothing written")
        return 0

    for jf, md_path, text in converted:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(text)
        os.remove(jf)
    print(f"  migrated {len(converted)} item(s) to Markdown + YAML frontmatter")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="convert + verify only, write nothing")
    args = ap.parse_args()
    sys.exit(migrate(dry_run=args.dry_run))
