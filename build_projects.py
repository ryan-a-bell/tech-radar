#!/usr/bin/env python3
"""
build_projects.py — aggregate the Markdown project files in projects/ into
data/projects.json for the PROJECTS tab (web/projects.html).

  python build_projects.py

Each projects/*.md is a project: a YAML-style front-matter block between `---`
fences, then a free-text body (see projects/README.md for the format). This
script parses them, resolves each project's declared `stack` against the
technology radar (by id or exact name), and writes one aggregate JSON file.

Two halves, per project:
  - declared stack     — the tools you ARE using, resolved to radar items
  - body               — prose the recommender embeds to suggest MORE tools

The recommendations themselves are computed in the browser (or, if you run
build_similarity.py, from precomputed embeddings) — this script only produces
the authoritative project records + declared mappings.

No third-party packages: the front-matter parser is a small hand-rolled reader
tuned to the handful of shapes the format uses (scalars, inline `[a, b]` lists,
and `- item` block lists). It is not a general YAML parser.

Output shape (data/projects.json):
  { "generated": "2026-07-15",
    "projects": [
      { "id", "name", "status", "topics": [...], "repo",
        "blurb", "body",
        "stack": [ {id, name, quadrant, ring, url, canonical_url} ],
        "stack_unresolved": ["..."] } ] }
"""

import datetime as _dt
import glob
import json
import os

import radar_core

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(HERE, "projects")
OUT = os.path.join(HERE, "data", "projects.json")

STATUSES = ["Idea", "Active", "Paused", "Shipped", "Archived"]


# --- front-matter + body ----------------------------------------------------
def _parse_scalar(raw):
    """Strip quotes/whitespace from a scalar value; '' -> None."""
    v = raw.strip()
    if (len(v) >= 2) and v[0] in "\"'" and v[-1] == v[0]:
        v = v[1:-1]
    return v or None


def _parse_inline_list(raw):
    """[a, b, "c d"] -> ['a', 'b', 'c d']. Empty/'[]' -> []."""
    inner = raw.strip()
    if inner.startswith("["):
        inner = inner[1:]
    if inner.endswith("]"):
        inner = inner[:-1]
    return [x for x in (_parse_scalar(p) for p in inner.split(",")) if x]


def parse_front_matter(text):
    """Split a Markdown file into (front_matter_dict, body_string).

    Recognises a leading `---` fenced block. Supported inside it:
      key: value                 -> scalar (or None if blank)
      key: [a, b, c]             -> list
      key:                       -> followed by `- item` lines -> list
    Anything after the closing fence is the body. If there is no front-matter
    fence, the whole text is the body and the dict is empty.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    fm = {}
    i = 1
    pending_key = None            # a `key:` awaiting `- item` block lines
    end = None
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            end = i
            break
        stripped = line.strip()

        # block-list continuation: `  - item`
        if pending_key is not None and stripped.startswith("- "):
            val = _parse_scalar(stripped[2:])
            if val:
                # the key was seeded as None when we saw `key:` with no value;
                # promote it to a list on the first `- item`
                if not isinstance(fm.get(pending_key), list):
                    fm[pending_key] = []
                fm[pending_key].append(val)
            i += 1
            continue
        pending_key = None

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if ":" in stripped:
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest.startswith("["):
                fm[key] = _parse_inline_list(rest)
            elif rest == "":
                # could be an empty scalar or the head of a block list;
                # decide when we see (or don't see) `- item` lines next
                fm[key] = None
                pending_key = key
            else:
                fm[key] = _parse_scalar(rest)
        i += 1

    body = "\n".join(lines[end + 1:]).strip() if end is not None else ""
    # a `key:` that turned out to have block-list items is now a list; one with
    # neither value nor items stays None — normalise both away downstream.
    return fm, body


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def first_paragraph(body):
    """First non-empty paragraph of the body — used as the card blurb."""
    para = []
    for line in body.splitlines():
        if line.strip():
            para.append(line.strip())
        elif para:
            break
    return " ".join(para)


# --- stack resolution against the radar -------------------------------------
def build_tool_index(items):
    """Return {lookup_key: item} for resolving `stack` entries by id or name.
    Keys: exact id, id without the 'source:' prefix, and lowercased name."""
    idx = {}
    for it in items:
        iid = it.get("id")
        if iid:
            idx[iid] = it
            if ":" in iid:
                idx.setdefault(iid.split(":", 1)[1], it)
        name = it.get("name")
        if name:
            idx.setdefault(name.lower(), it)
    return idx


def resolve_stack(entries, tool_index):
    """Map declared stack entries to compact radar refs. Returns
    (resolved_list, unresolved_list). Order is preserved; dups dropped."""
    resolved, unresolved, seen = [], [], set()
    for entry in entries:
        it = tool_index.get(entry) or tool_index.get(str(entry).lower())
        if not it:
            unresolved.append(entry)
            continue
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        resolved.append({
            "id": it["id"],
            "name": it.get("name"),
            "quadrant": it.get("quadrant"),
            "ring": it.get("ring"),
            "url": it.get("url"),
            "canonical_url": it.get("canonical_url"),
        })
    return resolved, unresolved


# --- assembly ---------------------------------------------------------------
def load_projects():
    """Parse every projects/*.md (except README.md) into raw dicts."""
    out = []
    if not os.path.isdir(PROJECTS_DIR):
        return out
    for path in sorted(glob.glob(os.path.join(PROJECTS_DIR, "*.md"))):
        if os.path.basename(path).lower() == "readme.md":
            continue
        with open(path, encoding="utf-8") as f:
            fm, body = parse_front_matter(f.read())
        default_id = os.path.splitext(os.path.basename(path))[0]
        out.append({"_path": path, "fm": fm, "body": body, "default_id": default_id})
    return out


def build_project_records():
    """Return the list of assembled project records (the payload's projects)."""
    items = radar_core.load_all_items()
    tool_index = build_tool_index(items)

    records = []
    for raw in load_projects():
        fm, body = raw["fm"], raw["body"]
        status = fm.get("status") or "Idea"
        if status not in STATUSES:
            print(f"  warning: {os.path.basename(raw['_path'])}: unknown status "
                  f"{status!r} (expected one of {STATUSES})")
        topics, bad_topics = radar_core.normalize_topics(_as_list(fm.get("topics")))
        if bad_topics:
            print(f"  warning: {os.path.basename(raw['_path'])}: topics not in the "
                  f"vocabulary: {', '.join(map(str, bad_topics))}")
        stack, unresolved = resolve_stack(_as_list(fm.get("stack")), tool_index)
        if unresolved:
            print(f"  warning: {os.path.basename(raw['_path'])}: stack entries not "
                  f"on the radar: {', '.join(map(str, unresolved))}")
        records.append({
            "id": fm.get("id") or raw["default_id"],
            "name": fm.get("name") or fm.get("id") or raw["default_id"],
            "status": status,
            "topics": topics,
            "repo": fm.get("repo"),
            "blurb": first_paragraph(body),
            "body": body,
            "stack": stack,
            "stack_unresolved": unresolved,
        })
    return records


def build_projects_json():
    """Write data/projects.json. Returns the number of projects."""
    records = build_project_records()
    payload = {
        "generated": _dt.date.today().isoformat(),
        "projects": records,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return len(records)


def main():
    n = build_projects_json()
    print(f"built projects.json ({n} project{'s' if n != 1 else ''})")


if __name__ == "__main__":
    main()
