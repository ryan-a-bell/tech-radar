---
name: "source-command-learning-manage"
description: "Manage the Learning Library — books, articles, videos, certifications, and conferences. Track reading/consumption status, rate finished items, set topics, shelve, record a conference's year editions, or add new learning material."
---

# source-command-learning-manage

Use this skill when the user asks to run the migrated source command
`learning-manage`, or asks to manage learning material — books, articles,
videos, courses, certifications, or conferences; reading/attendance status,
progress, ratings, or "what should I read next." To refresh recurring
conferences' dates from their websites, use `conference-track`. For
technologies, tools, libraries, frameworks, and platforms use `radar-manage`.

## Command Template

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
`Reading`/`Read` just mean "in progress" / "done".

## Types & their length fields

| Type | Length field | Also carries |
|------|--------------|--------------|
| book | `pages` / `pages_read` | — |
| article | `minutes` (read time) | `source`, `url` |
| video | `duration` (e.g. "1h 56m") | `source`, `url` |
| certification | `price` (exam fee) | `source` (exam code), `url`, `author` = issuer |
| conference | `editions` (one per year) | `recurrence`, `url`, `author` = organizer |

## Conferences (the recurring type)

A conference recurs, so one item tracks the whole series and each year is an
entry in its `editions` list (`year | dates | location | status | cfp | url`).
Add the series with `--type conference`, then record each year with `edition`
(an upsert keyed by `--year`; `--loc` aliases `--location`):

```bash
python learning.py add "RAMS" --type conference --author "IEEE, ASQ, SAE" \
  --url "https://rams.org/" --topics "Skills" --status Queued --blurb "..."
python learning.py edition RAMS --year 2026 --dates "2026-01-19..01-22" \
  --location "Miramar Beach, FL" --status Registered
```

Edition `status`: **Announced** → **Interested** → **Registered** →
**Attended**, plus **Skipped**. To pull dates/locations/CFP deadlines from a
conference's site automatically, use the **`conference-track`** skill.

## Topics

Curated `topics` list — the **same vocabulary as the tech radar**: **AI, ML,
Agents, Skills, Prompts, Trading, Quant, RAG, Data Feeds**. Assign with
`set <item> topics "ML,AI"`, filter with `list --topic Quant`.

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
a unique partial title (`prado`). Ambiguous partials are rejected.

## Adding an item by hand

`add` is for learning material the user names directly. Before running it,
actually go look at the source (the book's page, the article, the cert exam
guide) and read enough to write a real `--blurb` — one honest sentence, not a
copy-pasted tagline.

1. Pick the `--type` (`book`, `article`, `video`, `certification`,
   `conference`). For a conference, follow with `edition` to record its years.
2. Set `--author` (issuing org for a certification), `--topics` from the
   vocabulary, and the type's length field (`--pages` / `--minutes` /
   `--duration` / `--price`).
3. For articles/videos/certs, add `--source` and `--url`.
4. Write a real `--blurb`.
5. `add` lands in Discovered by default; pass `--status Queued` if already
   decided.
6. Tell the user what you found in a short summary.

## Notes

- `set` handles: `rating`, `pages_read`, `pages`, `minutes`, `duration`,
  `price`, `recurrence`, `topics`, `blurb`, `author`, `source`, `url`, `title`,
  `year`, `shelved_note`. `rating` is bounded 1–5; `topics` is validated.
  Conference editions are managed with `edition`, not `set`.
- `shelve` is `status … Shelved` plus a `--note`. Moving back out of Shelved
  clears the `shelved` date and note.
- The source of truth is `learning/*.md` — never edit the generated
  `data/learning.json` by hand. Prefer the CLI (it writes the Markdown and
  rebuilds the JSON); if you do hand-edit a `learning/<id>.md`, run
  `python build_learning.py` to republish. See `learning/README.md` for the
  file format.
