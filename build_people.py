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

A person also carries an optional CONTACT block — the rolodex fields. These are
purely additive: plain front-matter scalars (organization, business, location,
relationship, how_met, email, phone, last_contact), four flat link handles
(website, github, linkedin, x), and a `notes` block list where each item may be
prefixed `YYYY-MM-DD:` to date it. None of these feed the recommender; the bio
text still drives the semantic matching exactly as before.

Output shape (data/people.json):
  { "generated": "2026-07-16",
    "people": [
      { "id", "name", "role", "topics": [...], "interests": [...],
        "blurb", "body",
        "skills": [ {id, name, quadrant, ring, url, canonical_url} ],
        "skills_freeform": ["Python", "options pricing", ...],
        "contact": { "organization", "business", "location", "relationship",
                     "how_met", "email", "phone", "last_contact",
                     "links": {"website", "github", "linkedin", "x"} },
        "notes": [ {"when": "2026-08-01"|None, "text": "..."} ] } ] }
"""

import datetime as _dt
import glob
import json
import os
import re

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

# rolodex / contact block — all optional, all additive.
CONTACT_SCALARS = ("organization", "business", "location", "relationship",
                   "how_met", "email", "phone", "last_contact")
# flat link handles → assembled into contact["links"]; stored bare (a username
# or bare domain), the browser expands them to full URLs.
LINK_KEYS = ("website", "github", "linkedin", "x")
_NOTE_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*:\s*(.*)$", re.S)


def _clean(v):
    """A front-matter value as a trimmed string, or None if empty/missing."""
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def build_contact(fm):
    """Assemble the optional contact block from front-matter.

    Always returns a dict (fields default to None, links to {}) so the browser
    can render the card uniformly whether or not a person has contact info.
    """
    contact = {k: _clean(fm.get(k)) for k in CONTACT_SCALARS}
    links = {}
    for k in LINK_KEYS:
        v = _clean(fm.get(k))
        if v:
            links[k] = v
    contact["links"] = links
    return contact


def parse_notes(fm):
    """Parse the `notes` block list into dated note records.

    Each note is a free-text line; a leading `YYYY-MM-DD:` is peeled off into
    `when` so the browser can show it as a running, dated log. Undated notes
    keep `when: None`.
    """
    out = []
    for raw in _as_list(fm.get("notes")):
        s = _clean(raw)
        if not s:
            continue
        m = _NOTE_DATE.match(s)
        if m:
            out.append({"when": m.group(1), "text": m.group(2).strip()})
        else:
            out.append({"when": None, "text": s})
    return out


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
            "contact": build_contact(fm),
            "notes": parse_notes(fm),
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
