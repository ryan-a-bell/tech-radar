# tech-radar — repo guide

A personal technology radar plus a companion Learning Library. Scrapers
discover technologies and park them in a Discovered inbox; a human curates
them into rings. The Learning Library tracks the books, articles, videos, and
certifications alongside the tech they relate to. Both render to static pages
under `web/` and read their data from `data/`.

## Skill routing — which skill for which request

Two management skills cover two different collections. **Route by what the
item *is*, not by the word the user happened to use** — "add X", "what's in
progress", "promote this", "rate it" are ambiguous on their own; the object
decides. When a request is genuinely ambiguous, ask which collection before
running anything.

| If the request is about… | Use | Data it touches |
|---|---|---|
| A **technology** — tool, library, framework, platform, language, technique; anything with a repo/vendor/docs you'd *adopt or use* | **`radar-manage`** (`radar.py`) | `data/items/**` → rebuilds `data/radar.json` |
| **Learning material** — a book, article, video, course, certification, or conference; anything you *read/watch/study/attend* | **`learning-manage`** (`learning.py`) | `learning/**` → rebuilds `data/learning.json` |
| **Conference updates** — checking/refreshing recurring conferences (INCOSE IS, RAMS) for newly announced or changed year-over-year editions | **`conference-track`** (`learning.py edition` + WebFetch) | `learning/**` → rebuilds `data/learning.json` |

Concrete cues:

- **radar-manage** — rings (Discovered / Assess / Trial / Adopted / Archived),
  quadrants (Techniques / Tools / Platforms / Languages), `promote` / `demote`
  / `archive`, momentum, "is this trending", triaging the scraper's inbox.
- **learning-manage** — consumption status (Discovered / Queued / Reading /
  Read / Shelved), types (book / article / video / certification /
  conference), ratings, `pages_read`, `shelve`, "what should I read next",
  exam/cert tracking, adding a conference or one of its year editions.
- **conference-track** — "check my conferences", "any new INCOSE/RAMS dates",
  "when's the next <conference>", refreshing edition dates/locations/CFP
  deadlines from the conferences' own websites.

Both collections share the **same topic vocabulary** (AI, ML, Agents, Skills,
Prompts, Trading, Quant, RAG, Data Feeds) so a book and a technology can carry
the same topic — a shared topic is *not* a signal that they're the same
collection. A certification about a platform still lives in the Learning
Library, not on the radar; the platform itself lives on the radar.

## Conventions

- **Never hand-edit the generated JSON.** `data/radar.json` and
  `data/learning.json` are build artifacts. Go through `radar.py` /
  `learning.py` (or, for a bulk change, edit the source files and rebuild) so
  the dashboard never sees a half-written file. The Learning Library's source
  of truth is now `learning/*.md` (one file per item, like `people/` and
  `projects/`); a hand-edit there is fine, just run `python build_learning.py`
  to republish `data/learning.json`.
- **Don't commit the regenerated aggregate JSON.** `data/radar.json`,
  `data/learning.json`, `data/projects.json`, and `data/people.json` are build
  artifacts that `build_site.py` regenerates from their per-item sources at
  deploy time (step 1 rebuilds `radar.json` from `data/items/**` before it's
  copied into `site/`), so the deployed dashboard never depends on the committed
  copy. `radar.py` rewrites `data/radar.json` locally after every command as a
  side effect — just leave that change out of your commit (`git add data/items/`
  or `git checkout data/radar.json` before committing). Commit only the per-item
  source file (`data/items/**`, `learning/*.md`, `projects/*.md`, `people/*.md`);
  that's the source of truth. (The daily discovery Action commits a fresh
  `radar.json` to `main` on its own schedule, so the repo copy self-heals.)
- When **adding** an item to either collection, actually open the source and
  read enough to write a real one-to-two-sentence description/blurb first — no
  placeholder or copied-tagline entries.
- Both CLIs match an item by exact id, exact name/title, or a *unique* partial;
  ambiguous partials are rejected with the list of matches.

## Tests

`python -m unittest discover -s tests` — stdlib `unittest`, no fixtures touch
disk. `radar_core` and `learning_core` are pure and covered there.
