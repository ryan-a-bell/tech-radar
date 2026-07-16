#!/usr/bin/env python3
"""
build_people.py — aggregate the Markdown people files in people/ into
data/people.json for the PEOPLE tab (web/people.html).

  python build_people.py

Each people/*.md is a person: a YAML-style front-matter block between `---`
fences, then a free-text bio (see people/README.md for the format). This script
parses them, resolves each person's declared `skills` against the technology
radar (by id or exact name), and writes one aggregate JSON file.

A person is deliberately shaped like a project: a resolved list of radar refs
(here `skills` instead of a project's `stack`) plus prose the recommender
embeds. The one addition is `interests` — growth topics, so the browser can
bias tech recommendations toward new ground rather than more of the same
("hybrid" framing: current skills AND where they want to go).

`skills` entries that resolve against the radar become linked, quadrant-coloured
skills; entries that don't (`Python`, `options pricing`) are kept as free-form
skill tags. Unlike a project's unresolved stack, a free-form skill is expected,
not a warning — most people have skills that aren't radar tools.

The recommendations themselves (tech to check out, matching projects, similar
people) are computed in the browser via the same TF-IDF space the Projects page
uses — this script only produces the authoritative person records + resolved
skill mappings.

Output shape (data/people.json):
  { "generated": "2026-07-16",
    "people": [
      { "id", "name", "role", "topics": [...], "interests": [...],
        "blurb", "body",
        "skills": [ {id, name, quadrant, ring, url, canonical_url} ],
        "skills_freeform": ["Python", "options pricing", ...] } ] }
"""

import datetime as _dt
import glob
import json
import os

import radar_core

# reuse the project front-matter parser and radar-resolution helpers verbatim —
# a person's `skills` is resolved exactly like a project's `stack`.
from build_projects import (
    parse_front_matter,
    first_paragraph,
    build_tool_index,
    resolve_stack,
    _as_list,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PEOPLE_DIR = os.path.join(HERE, "people")
OUT = os.path.join(HERE, "data", "people.json")


def load_people():
    """Parse every people/*.md (except README.md) into raw dicts."""
    out = []
    if not os.path.isdir(PEOPLE_DIR):
        return out
    for path in sorted(glob.glob(os.path.join(PEOPLE_DIR, "*.md"))):
        if os.path.basename(path).lower() == "readme.md":
            continue
        with open(path, encoding="utf-8") as f:
            fm, body = parse_front_matter(f.read())
        default_id = os.path.splitext(os.path.basename(path))[0]
        out.append({"_path": path, "fm": fm, "body": body, "default_id": default_id})
    return out


def build_person_records():
    """Return the list of assembled person records (the payload's people)."""
    items = radar_core.load_all_items()
    tool_index = build_tool_index(items)

    records = []
    for raw in load_people():
        fm, body = raw["fm"], raw["body"]

        topics, bad_topics = radar_core.normalize_topics(_as_list(fm.get("topics")))
        if bad_topics:
            print(f"  warning: {os.path.basename(raw['_path'])}: topics not in the "
                  f"vocabulary: {', '.join(map(str, bad_topics))}")

        interests, bad_interests = radar_core.normalize_topics(_as_list(fm.get("interests")))
        if bad_interests:
            print(f"  warning: {os.path.basename(raw['_path'])}: interests not in the "
                  f"vocabulary: {', '.join(map(str, bad_interests))}")

        # radar-backed skills resolve to compact refs; the rest are free-form
        # skill tags (Python, statistics, …) — normal, not a warning.
        skills, freeform = resolve_stack(_as_list(fm.get("skills")), tool_index)

        records.append({
            "id": fm.get("id") or raw["default_id"],
            "name": fm.get("name") or fm.get("id") or raw["default_id"],
            "role": fm.get("role") or "",
            "topics": topics,
            "interests": interests,
            "blurb": first_paragraph(body),
            "body": body,
            "skills": skills,
            "skills_freeform": freeform,
        })
    return records


def build_people_json():
    """Write data/people.json. Returns the number of people."""
    records = build_person_records()
    payload = {
        "generated": _dt.date.today().isoformat(),
        "people": records,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return len(records)


def main():
    n = build_people_json()
    print(f"built people.json ({n} {'person' if n == 1 else 'people'})")


if __name__ == "__main__":
    main()
