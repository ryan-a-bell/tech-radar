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
        "stack_unresolved": ["..."],
        "artifacts": { "models": [...], "risks": {...} | null, "files": [...] } } ] }

Artifacts are optional engineering data dropped next to the project under
projects/artifacts/<project-id>/:
  *.sysml          — SysML v2 textual models, summarised (packages, defs, trace)
  *risk*.csv       — a risk register export (CMPro or any tool that writes CSV),
                     scored on the 5x5 likelihood x consequence matrix
  anything else    — listed as a plain linked file (PDFs, diagrams, ICDs, ...)
"""

import csv
import datetime as _dt
import glob
import io
import json
import os
import re

import radar_core

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(HERE, "projects")
ARTIFACTS_DIR = os.path.join(PROJECTS_DIR, "artifacts")
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


# --- artifacts: SysML v2 models ---------------------------------------------
_SYSML_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
_SYSML_NAME = r"(?:<'?[^>']*'?>\s*)?('[^']+'|[A-Za-z_]\w*)"
_SYSML_PACKAGE = re.compile(r"\b(?:library\s+)?package\s+" + _SYSML_NAME)
_SYSML_DEF = re.compile(
    r"\b(part|port|item|attribute|action|state|requirement|interface|connection|"
    r"constraint|calc|analysis|verification|enum|allocation|flow|use\s+case)\s+def\s+"
    + _SYSML_NAME)
_SYSML_REQ_ID = re.compile(r"\brequirement\s+(?:def\s+)?<'?([^>']+)'?>\s*" + _SYSML_NAME)
_SYSML_SATISFY = re.compile(r"(?<!\w)satisfy\s+(?:requirement\s+)?([\w':]+)")
_SYSML_USAGE = {
    "parts": re.compile(r"(?<!\w)part\s+(?!def\b)[A-Za-z_']"),
    "ports": re.compile(r"(?<!\w)port\s+(?!def\b)[A-Za-z_']"),
    "connections": re.compile(r"(?<!\w)connect\s"),
    "satisfy": re.compile(r"(?<!\w)satisfy\s"),
    "verify": re.compile(r"(?<!\w)verify\s"),
    "allocate": re.compile(r"(?<!\w)allocate\s"),
}


def _unquote(name):
    return name[1:-1] if name.startswith("'") and name.endswith("'") else name


def summarize_sysml(text):
    """Summarise a SysML v2 textual model without a full parser: packages,
    definitions by kind, requirement ids, and usage / trace-link counts."""
    src = _SYSML_COMMENT.sub(" ", text)
    defs = {}
    for kind, name in _SYSML_DEF.findall(src):
        kind = re.sub(r"\s+", " ", kind)
        defs.setdefault(kind, []).append(_unquote(name))
    return {
        "packages": [_unquote(n) for n in _SYSML_PACKAGE.findall(src)],
        "defs": defs,
        "requirements": [{"id": rid, "name": _unquote(n)}
                         for rid, n in _SYSML_REQ_ID.findall(src)],
        "satisfied": sorted({_unquote(n.split("::")[-1]) for n in _SYSML_SATISFY.findall(src)}),
        "counts": {k: len(rx.findall(src)) for k, rx in _SYSML_USAGE.items()},
    }


# --- artifacts: risk registers ----------------------------------------------
# Header aliases so exports from different tools (CMPro, Active Risk Manager,
# a hand-kept spreadsheet) map onto one shape. Matched case-insensitively.
RISK_COLUMNS = {
    "id": ["id", "risk id", "risk_id", "risk #", "risk no", "number", "no"],
    "title": ["title", "risk title", "risk", "name", "risk statement", "description"],
    "likelihood": ["likelihood", "probability", "prob", "l"],
    "consequence": ["consequence", "impact", "severity", "c"],
    "status": ["status", "state"],
    "owner": ["owner", "risk owner", "assignee"],
    "mitigation": ["mitigation", "mitigation plan", "handling", "response", "handling strategy"],
}

# DoD Risk, Issue, and Opportunity guide 5x5 matrix — rows are likelihood 1..5,
# columns consequence 1..5.
RISK_MATRIX = [
    "LLLLM",
    "LLLMM",
    "LLMMH",
    "LMMHH",
    "LMHHH",
]
RISK_LEVEL = {"L": "Low", "M": "Moderate", "H": "High"}
CLOSED_STATUSES = {"closed", "retired", "realized", "accepted"}


def risk_level(likelihood, consequence):
    """Low / Moderate / High for a 1..5 likelihood and consequence, else None."""
    if not (1 <= likelihood <= 5 and 1 <= consequence <= 5):
        return None
    return RISK_LEVEL[RISK_MATRIX[likelihood - 1][consequence - 1]]


def _int_or_none(v):
    m = re.match(r"\s*(\d+)", v or "")
    return int(m.group(1)) if m else None


def parse_risk_register(text):
    """Parse a risk-register CSV into {risks: [...], unmapped: [...]}. Rows
    without a likelihood and consequence are kept but left unscored."""
    reader = csv.DictReader(io.StringIO(text))
    headers = {h.strip().lower(): h for h in (reader.fieldnames or []) if h}
    colmap = {}
    for field, aliases in RISK_COLUMNS.items():
        for a in aliases:
            if a in headers and headers[a] not in colmap.values():
                colmap[field] = headers[a]
                break
    risks = []
    for row in reader:
        get = lambda f: (row.get(colmap[f]) or "").strip() if f in colmap else ""
        if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
            continue
        lik, con = _int_or_none(get("likelihood")), _int_or_none(get("consequence"))
        level = risk_level(lik, con) if lik and con else None
        status = get("status") or "Open"
        risks.append({
            "id": get("id") or f"R{len(risks) + 1}",
            "title": get("title"),
            "likelihood": lik,
            "consequence": con,
            "score": lik * con if level else None,
            "level": level,
            "status": status,
            "open": status.lower() not in CLOSED_STATUSES,
            "owner": get("owner") or None,
            "mitigation": get("mitigation") or None,
        })
    risks.sort(key=lambda r: (not r["open"], -(r["score"] or 0), r["id"]))
    return {"risks": risks, "unmapped": sorted(set(RISK_COLUMNS) - set(colmap))}


def load_artifacts(project_id, root=ARTIFACTS_DIR):
    """Collect projects/artifacts/<project_id>/** into the record's artifacts
    block, or None when the project has no artifact folder."""
    base = os.path.join(root, project_id)
    if not os.path.isdir(base):
        return None
    models, files, risks, sources = [], [], [], []
    for path in sorted(glob.glob(os.path.join(base, "**", "*"), recursive=True)):
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, base).replace(os.sep, "/")
        href = "projects/artifacts/" + project_id + "/" + rel
        name = os.path.basename(path)
        low = name.lower()
        if low.endswith(".sysml"):
            with open(path, encoding="utf-8") as f:
                models.append({"file": rel, "href": href, **summarize_sysml(f.read())})
        elif low.endswith(".csv") and "risk" in low:
            with open(path, encoding="utf-8-sig") as f:
                reg = parse_risk_register(f.read())
            if reg["unmapped"]:
                print(f"  warning: {project_id}/{rel}: risk columns not found: "
                      f"{', '.join(reg['unmapped'])}")
            risks.extend(reg["risks"])
            sources.append({"file": rel, "href": href})
        else:
            files.append({"file": rel, "href": href, "bytes": os.path.getsize(path)})
    return {
        "models": models,
        "risks": {"items": risks, "sources": sources} if sources else None,
        "files": files,
    }


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
        pid = fm.get("id") or raw["default_id"]
        records.append({
            "id": pid,
            "name": fm.get("name") or fm.get("id") or raw["default_id"],
            "status": status,
            "topics": topics,
            "repo": fm.get("repo"),
            "blurb": first_paragraph(body),
            "body": body,
            "stack": stack,
            "stack_unresolved": unresolved,
            "artifacts": load_artifacts(pid),
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
