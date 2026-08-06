#!/usr/bin/env python3
"""
build_learning.py — aggregate the Markdown learning files in learning/ into
data/learning.json for the LEARNING tab (web/learning.html).

  python build_learning.py

Each learning/*.md is one item (book · article · video · certification): a
YAML-style front-matter block between `---` fences, then a free-text body that
is the blurb (see learning/README.md for the format). This script parses them
via learning_core and writes one aggregate JSON file.

This mirrors how build_projects.py / build_people.py turn people/*.md and
projects/*.md into their aggregate JSON. The Learning Library page reads the
generated data/learning.json directly, so running this IS the publish step for
hand-edited files; the learning.py CLI runs it for you after every write.

Output shape (data/learning.json):
  { "generated": "<date>", "items": [ {...}, {...} ] }
"""

import datetime as _dt
import json
import os

import learning_core as core

OUT = core.LEARNING_JSON


def build_learning_json(day=None):
    """Read learning/*.md and (re)write data/learning.json. Returns the item
    count. `ensure_ascii=True` keeps the on-disk JSON byte-identical in style to
    what the old single-file store produced (unicode escaped as \\uXXXX)."""
    items = core.load_items()
    doc = {"generated": day or _dt.date.today().isoformat(), "items": items}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return len(items)


if __name__ == "__main__":
    n = build_learning_json()
    print(f"built learning.json ({n} items)")
