# Projects

Personal projects, tracked in Markdown and mapped against the technology
radar. This directory is deliberately kept **separate** from `data/` (the
technology stuff) — projects are hand-written prose, not scraped JSON.

`build_projects.py` reads every `*.md` here (except this README), resolves the
declared `stack` against the radar, and writes `data/projects.json`, which the
**PROJECTS** tab (`web/projects.html`) renders.

## File format

Each project is one Markdown file: a YAML-style front-matter block between
`---` fences, followed by a free-text body.

```markdown
---
id: options-vol-surface          # unique slug (defaults to the filename)
name: Options Vol-Surface Lab     # display name
status: Idea                      # Idea | Active | Paused | Shipped | Archived
topics: [Quant, Trading]          # from the radar's TOPICS vocabulary
stack: [manual:financepy, QuantPy]  # tools you ARE using — ids or names on the radar
repo: https://github.com/you/vol-surface
---

Everything below the closing fence is the body. This prose is what the
semantic recommender reads, so describe what the project *does* and the
problems it solves — that is what gets matched against tool descriptions.
```

### Fields

| Field | Required | Notes |
|-------|----------|-------|
| `id` | no | Unique slug. Defaults to the filename without `.md`. |
| `name` | no | Display name. Defaults to `id`. |
| `status` | no | `Idea`, `Active`, `Paused`, `Shipped`, or `Archived`. Defaults to `Idea`. |
| `topics` | no | List from the shared `TOPICS` vocabulary (`radar_core.py`). |
| `stack` | no | Tools you are **using** — referenced by radar `id` (`manual:cursor`) or by exact `name` (`Cursor`). Unresolved entries are surfaced as a warning, not an error. |
| `repo` | no | Link shown on the project card. |
| _body_ | recommended | Prose used for tool recommendations. The first paragraph becomes the card blurb. |

## The two halves: declared vs. recommended

- **Declared stack** (`stack:`) — the authoritative "we ARE using these tools"
  record. Fully human-owned, deterministic.
- **Recommended tools** — computed by cosine similarity between the project
  body and every tool's description. For a project with a `stack`, these are
  *adjacent* tools you might add; for an `Idea` with no stack, this **is** the
  suggested tech stack, derived purely from the semantics of the idea.

The recommender works out of the box using in-browser TF-IDF. Running
`build_similarity.py` upgrades it to true semantic embeddings
(`data/project_similarity.json`) — same optional quality path as the Tool
Similarity page.

## Workflow

```bash
# 1. add or edit a project file here, then rebuild the aggregate
python build_projects.py

# 2. (optional) upgrade recommendations to semantic embeddings
python build_similarity.py

# 3. build the static site and preview
python build_site.py
cd site && python -m http.server 8000   # open projects.html
```
