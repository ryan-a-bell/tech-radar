# Learning Library

The books, articles, videos, certifications, and conferences tracked alongside
the tech radar, each one a Markdown file. Like `people/` and `projects/`, this
directory is the **source of truth** — hand-written prose, not scraped JSON.

`build_learning.py` reads every `*.md` here (except this README) and writes
`data/learning.json`, which the **LEARNING** tab (`web/learning.html`) renders.
The `learning.py` CLI writes these files for you and refreshes the JSON in the
same step, so you rarely edit them by hand — but you can.

## File format

Each item is one Markdown file named `<id>.md`: a YAML-style front-matter block
between `---` fences (the structured fields), followed by a free-text body that
is the **blurb**.

```markdown
---
id: ddia                          # unique slug (defaults to the filename)
type: book                        # book | article | video | certification | conference
title: Designing Data-Intensive Applications
author: Martin Kleppmann
year: 2017
status: Read                      # Read | Reading | Queued | Discovered | Shelved
topics: [Data Feeds, Skills]      # from the shared TOPICS vocabulary
pages: 616                        # book length
pages_read:                       # blank = not tracked (parses to null)
rating: 5                         # 1–5, set once Read
added:                            # status date stamps (added/queued/started/
started:                          #   finished/shelved) — set as the item moves
queued:
finished: 2026-03-02
shelved:
---

The reference for how reliable, scalable systems actually store and move
data — replication, partitioning, and the tradeoffs behind every database
pitch deck. This body is the blurb.
```

A blank `key:` parses to `null`; every field is written out even when empty so
you can see what's fillable. Values with a leading `[`, wrapping quotes, or edge
whitespace are quoted — everything else (internal colons, commas, em-dashes) is
written bare.

### Fields

| Field | Notes |
|-------|-------|
| `id` | Unique slug. Defaults to the filename without `.md`. |
| `type` | `book`, `article`, `video`, `certification`, or `conference`. Decides the length field below. |
| `title` / `author` | Display fields. For a certification, `author` is the issuing org; for a conference, the organizer. |
| `year` | Publication/release year (integer). Blank for conferences — the year lives on each edition. |
| `status` | `Read`, `Reading`, `Queued`, `Discovered`, or `Shelved`. |
| `topics` | Inline list from the shared `TOPICS` vocabulary (`learning_core.py`). |
| length | `pages` + `pages_read` (book), `minutes` (article), `duration` (video), `price` (certification), `editions` (conference — see below). |
| `recurrence` | Conferences only: cadence, e.g. `annual` (default) / `biennial`. |
| `rating` | 1–5, set once the item is Read. |
| dates | `added`, `queued`, `started`, `finished`, `shelved` — stamped as the item moves through the pipeline. |
| `shelved_note` | Optional one-liner on why something was set aside; cleared when it leaves Shelved. |
| `source` / `url` | Publication/channel (or exam code) + link, for articles/videos/certifications/conferences. Books carry neither. |
| _body_ | The blurb — one honest sentence or two about what the item is. |

### Conferences & their editions

A conference (INCOSE IS, RAMS) **recurs**, so one file tracks the whole series
and every year's occurrence is one line in an `editions` block list. Each
edition is a single pipe-delimited scalar — `year | dates | location | status |
cfp | url` — so the same block-list parser reads it, and the file stays
greppable and hand-editable. Trailing empty fields may be dropped.

```markdown
---
id: incose-international-symposium
type: conference
title: INCOSE International Symposium
author: INCOSE
url: https://www.incose.org/events-education/international-symposium/
recurrence: annual
status: Queued
topics: [Skills]
editions:
  - 2027 | 2027-07-17..07-22 |  | Announced
  - 2026 | 2026-06-13..06-18 | Yokohama, Japan | Registered | 2025-11-01
  - 2025 | 2025-07-26..07-31 | Ottawa, Canada | Attended
---

The flagship annual systems-engineering symposium — papers, tutorials, and
working-group sessions.
```

Edition `status` is its own small, content-neutral vocabulary (distinct from
the item's consumption `status`): **Announced** (dates known / on the radar) →
**Interested** → **Registered** → **Attended**, with **Skipped** for a year you
sat out. Editions are kept newest-first. Manage them with
`python learning.py edition <conf> --year YYYY …` (an upsert keyed by year); the
`conference-track` skill fills them in automatically from each conference's
website.

## Workflow

```bash
# preferred: let the CLI write the .md and refresh the JSON in one step
python learning.py add "Streaming Systems" --type book --topics "Data Feeds" \
  --blurb "Windowing, watermarks, and exactly-once semantics."
python learning.py status ddia Reading
python learning.py rate ddia 5

# a recurring conference: add the series, then record each year's edition
python learning.py add "RAMS" --type conference --author "IEEE" \
  --url "https://rams.org/" --topics "Skills" --blurb "Reliability symposium."
python learning.py edition RAMS --year 2026 --dates "2026-01-19..01-22" \
  --location "Miramar Beach, FL" --status Registered

# or hand-edit a learning/<id>.md, then republish:
python build_learning.py

# build the static site and preview
python build_site.py
cd site && python -m http.server 8000   # open learning.html
```
