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
| **Learning material** — a book, article, video, course, or certification; anything you *read/watch/study* | **`learning-manage`** (`learning.py`) | `data/learning.json` |

Concrete cues:

- **radar-manage** — rings (Discovered / Assess / Trial / Adopted / Archived),
  quadrants (Techniques / Tools / Platforms / Languages), `promote` / `demote`
  / `archive`, momentum, "is this trending", triaging the scraper's inbox.
- **learning-manage** — consumption status (Discovered / Queued / Reading /
  Read / Shelved), types (book / article / video / certification), ratings,
  `pages_read`, `shelve`, "what should I read next", exam/cert tracking.

Both collections share the **same topic vocabulary** (AI, ML, Agents, Skills,
Prompts, Trading, Quant, RAG, Data Feeds) so a book and a technology can carry
the same topic — a shared topic is *not* a signal that they're the same
collection. A certification about a platform still lives in the Learning
Library, not on the radar; the platform itself lives on the radar.

## Conventions

- **Never hand-edit the JSON.** Go through `radar.py` / `learning.py` so writes
  stay atomic and the generated files (`radar.json`, `learning.json`) stay
  consistent. Editing `data/**` directly risks a half-written dashboard.
- When **adding** an item to either collection, actually open the source and
  read enough to write a real one-to-two-sentence description/blurb first — no
  placeholder or copied-tagline entries.
- Both CLIs match an item by exact id, exact name/title, or a *unique* partial;
  ambiguous partials are rejected with the list of matches.

## Tests

`python -m unittest discover -s tests` — stdlib `unittest`, no fixtures touch
disk. `radar_core` and `learning_core` are pure and covered there.
