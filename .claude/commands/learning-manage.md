---
description: Manage the Learning Library — books, articles, videos, and certifications. Track reading/consumption status, rate finished items, set topics, shelve, or add new learning material.
---

# Learning Library — Management

The Learning Library is the human-curated companion to the tech radar: the
**books, articles, videos, and certifications** you're reading, watching, or
planning to. It's separate from the technology radar (that's `radar-manage`) —
if the thing is a tool/library/framework/platform, it belongs on the radar;
if it's *learning material about* a thing, it belongs here. The source of truth
is one Markdown file per item under `learning/` (like `people/` and
`projects/`). All changes go through `learning.py`, which writes the affected
`learning/*.md` and then rebuilds the generated `data/learning.json` the page
reads — so a CLI change still publishes immediately, in one step.

## Consumption status

Items move along a pipeline (most-resolved first, mirroring the radar's rings):

| Status | Meaning |
|--------|---------|
| Discovered | On the list, not started (the inbox) — stamps `added` |
| Queued | Decided to pursue it, hasn't started — stamps `queued` |
| Reading | In progress (books track `pages_read`) — stamps `started` |
| Read | Finished — set a `rating` (1–5); stamps `finished` |
| Shelved | Deliberate "not now" set-aside — stamps `shelved` + optional note |

Status is content-neutral: for an article, video, or certification,
`Reading`/`Read` just mean "in progress" / "done" (the page shows them as
*In Progress* / *Done*).

## Types & their length fields

Every item carries a `type`, and each type tracks a different "length":

| Type | Length field | Also carries |
|------|--------------|--------------|
| book | `pages` / `pages_read` | — |
| article | `minutes` (read time) | `source`, `url` |
| video | `duration` (e.g. "1h 56m") | `source`, `url` |
| certification | `price` (exam fee) | `source` (exam code), `url`, `author` = issuer |

## Topics

Items carry a curated `topics` list — the **same vocabulary as the tech
radar** so a book and a technology can share a topic: **AI, ML, Agents,
Skills, Prompts, Trading, Quant, RAG, Data Feeds**. Assign with
`set <item> topics "ML,AI"` and filter with `list --topic Quant`.

## Commands

```bash
python learning.py list                          # everything, grouped by status
python learning.py list --status Reading         # just what's in progress
python learning.py list --type certification     # only certifications
python learning.py list --topic Quant            # items carrying a topic
python learning.py show <id-or-title>            # full JSON for one item
python learning.py find <text>                   # search title/author/blurb

python learning.py status <id-or-title> Reading  # move along the pipeline
python learning.py rate <id-or-title> 5          # set a 1-5 rating
python learning.py shelve <id-or-title> --note "why, for now"
python learning.py set <id-or-title> pages_read 210
python learning.py set <id-or-title> topics "Quant,ML"

python learning.py add "<Title>" --type book --author "<who>" \
  --topics "ML,AI" --blurb "<one-liner>" [--pages N] [--year YYYY] \
  [--status Queued]                              # add an entry
```

Items can be named by exact id (`afml`), exact title (`Team Topologies`), or
a unique partial title (`prado`). Ambiguous partials are rejected with the
list of matches.

## Adding an item by hand

`add` is for learning material you name directly. Before running it, actually
go look at the source (the book's page, the article, the cert exam guide) and
read enough to write a real `--blurb` — one honest sentence on what it is and
why it's worth your time, not a copy-pasted marketing line.

1. Pick the `--type` (`book`, `article`, `video`, `certification`).
2. Set `--author` (issuing org for a certification), `--topics` from the
   vocabulary, and the type's length field (`--pages` / `--minutes` /
   `--duration` / `--price`).
3. For articles/videos/certs, add `--source` and `--url`.
4. Write a real `--blurb`.
5. `add` lands in Discovered by default; pass `--status Queued` (or run
   `status` after) if you've already decided to pursue it.
6. Tell the user what you found in a short summary, not just that it was added.

## Notes

- The `set` command handles: `rating`, `pages_read`, `pages`, `minutes`,
  `duration`, `price`, `topics`, `blurb`, `author`, `source`, `url`, `title`,
  `year`, `shelved_note`. `rating` is bounded 1–5; `topics` is validated.
- `shelve` is `status … Shelved` plus a `--note` explaining the set-aside.
  Moving an item back out of Shelved clears the `shelved` date and note.
- The source of truth is `learning/*.md` — never edit the generated
  `data/learning.json` by hand. Prefer the CLI (it writes the Markdown and
  rebuilds the JSON); if you do hand-edit a `learning/<id>.md`, run
  `python build_learning.py` to republish. See `learning/README.md` for the
  file format.
