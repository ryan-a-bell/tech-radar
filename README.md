# Tech Radar

A self-hosted technology radar that automatically discovers emerging technologies from GitHub Trending, Reddit, and RSS feeds, then lets you curate them through a CLI and view the results as an interactive static dashboard.

---

## How it works

```
GitHub Trending ──┐
Reddit            ├──► runner.py ──► data/items/ ──► data/radar.json ──► dashboard
RSS Feeds         ┘                       ▲
                                    radar.py (human curation)
```

1. **Discovery** — `runner.py` runs all scrapers, deduplicates across sources using canonical GitHub URLs, and writes one JSON file per technology into `data/items/`.
2. **Curation** — `radar.py` lets you triage the inbox (`Discovered` ring), promote items to `Assess`, `Trial`, or `Adopted`, archive dead tech, assign topics, and fix metadata. Every change rebuilds `data/radar.json` automatically.
3. **Deploy** — `build_site.py` assembles a self-contained `site/` folder you can push to GitHub Pages, Netlify, or serve locally.

---

## Prerequisites

- Python 3.8+ (no third-party packages — stdlib only)
- A modern browser (for the dashboard)
- No Node.js, no npm, no build step

---

## Quick start

```bash
# 1. Run discovery (writes to data/items/, builds data/radar.json)
python runner.py

# 2. See what was found
python radar.py list --ring Discovered

# 3. Promote something you like
python radar.py promote "Bun" Trial

# 4. Build the static site
python build_site.py

# 5. Preview in browser
cd site && python -m http.server 8000
# open http://localhost:8000
```

---

## Scripts

### `runner.py` — Discovery

```bash
python runner.py              # run all scrapers, then build radar.json
python runner.py --build      # only rebuild radar.json from existing items (no scraping)
python runner.py --dry-run    # discover and print, write nothing
```

The runner never touches items a human has already classified. Re-discovered technologies get their `last_seen` refreshed and their star count updated, but their ring and other curated fields are left alone.

### `radar.py` — Curation

```bash
python radar.py list                          # all items, grouped by ring
python radar.py list --ring Discovered        # the review inbox

python radar.py show <id-or-name>             # full JSON for one item
python radar.py find <text>                   # search name + description

python radar.py list --topic Agents           # items tagged with a topic
python radar.py list --ring Archived --older-than 90   # stale archives
python radar.py promote <id-or-name> Trial    # move to a ring
python radar.py demote <id-or-name>           # send back to Discovered
python radar.py set <id-or-name> quadrant Platforms
python radar.py set <id-or-name> company "Anthropic"
python radar.py set <id-or-name> topics "AI,Agents"   # curated topics
python radar.py archive <id-or-name>          # move to Archived (dated)
```

Items can be referenced by exact id (`github:oven-sh/bun`), exact name (`Bun`), or a unique partial name (`uv`).

### `build_site.py` — Deploy

```bash
python build_site.py    # produces ./site/ ready for static hosting
```

Strips the `export default` from `dashboard.jsx` so it runs under the CDN/Babel setup without a build step. It also copies `config.js` (which ships as `window.RADAR_EDIT = false`), keeping the deployed dashboard read-only.

### `edit_server.py` — Curate in the browser

```bash
python edit_server.py          # http://localhost:8001/
python edit_server.py 8080     # custom port
```

Serves the **same** `index.html` + `dashboard.jsx` as the public site, but
answers `GET /config.js` with `window.RADAR_EDIT = true`. That single flag
unlocks a ring editor in the detail panels; clicking a ring POSTs to
`/api/promote`, writes the change to `data/items/*.json`, and rebuilds
`radar.json` immediately — the same effect as `radar.py promote`, just visual.

There is one dashboard, not two. Edit affordances are gated behind the runtime
flag, so the deployed GitHub Pages build can't be edited — the flag is `false`
there and there is no backend to accept a write. Editing exists only on your
machine, only while `edit_server.py` is running.

---

## Tests

The pure logic in `radar_core.py` — canonical-URL dedup, star-trend, topic
normalization, id/path mapping — is covered by a stdlib `unittest` suite. No
third-party packages, nothing touches disk.

```bash
python -m unittest discover -s tests       # run everything
python -m unittest tests.test_radar_core   # one module
```

CI runs these before discovery or deploy, so a regression in the core can't
ship to the published radar.

---

## Data model

### Rings

| Ring | Meaning |
|------|---------|
| `Discovered` | Found by a scraper; not yet reviewed — the inbox |
| `Assess` | Worth a closer look or experiment |
| `Trial` | Actively using on real work |
| `Adopted` | Recommended default |
| `Archived` | Retired / dead / irrelevant — kept (dated via `archived_at`) so it won't re-surface |

Only a human moves items out of `Discovered`. Scrapers never classify.
Archiving stamps `archived_at`, so the graveyard can be filtered by age
(`list --ring Archived --older-than <days>`).

### Quadrants

`Techniques` · `Tools` · `Platforms` · `Languages`

### Topics

A curated, controlled vocabulary assigned per item, separate from the
free-form `tags` scrapers emit: `AI` · `ML` · `Agents` · `Skills` ·
`Prompts` · `Trading` · `Quant` · `RAG` · `Data Feeds` (extend `TOPICS` in
`radar_core.py`). Filter by topic in the dashboard or with `list --topic <name>`.
The same vocabulary is reused by the Reading List below, so a book and a
technology can share a topic tag.

### Item schema

```json
{
  "id": "github:oven-sh/bun",
  "name": "Bun",
  "description": "Incredibly fast JavaScript runtime",
  "quadrant": "Tools",
  "ring": "Trial",
  "source": "GitHub",
  "url": "https://github.com/oven-sh/bun",
  "canonical_url": "github.com/oven-sh/bun",
  "also_seen": [
    { "source": "Reddit", "url": "https://...", "seen": "2026-05-23" }
  ],
  "company": "Oven",
  "stars": 78900,
  "momentum": 72,
  "tags": ["runtime"],
  "first_seen": "2026-05-21",
  "last_seen": "2026-05-23",
  "stars_history": { "2026-05-21": 78900, "2026-05-23": 78950 },
  "trend": "up",
  "trend_delta": 50
}
```

`trend` and `trend_delta` are computed by `runner.py` at build time from `stars_history` — they are not stored in the per-item files.

---

## Reading List

A companion page (`web/books.html` + `web/books.jsx`) for tracking books
alongside the technologies they relate to. Hand-curated in `data/books.json`
(no scraper — add entries by editing the file directly). Read-only, same as
the deployed dashboard.

### Status

| Status | Meaning |
|--------|---------|
| `Discovered` | On the list, not started |
| `Reading` | In progress — tracks `pages_read` |
| `Read` | Finished — tracks `rating` (1–5) |

### Book schema

```json
{
  "id": "ddia",
  "title": "Designing Data-Intensive Applications",
  "author": "Martin Kleppmann",
  "year": 2017,
  "status": "Read",
  "topics": ["Data Feeds", "Skills"],
  "pages": 616,
  "pages_read": null,
  "rating": 5,
  "added": null,
  "started": null,
  "finished": "2026-03-02",
  "blurb": "..."
}
```

`topics` draws from the same `TOPICS` vocabulary as the tech radar (see
above). The page (an "Atlas" view, like the dashboard's) shows a radar plot —
rings for status, sectors for topic — pinned beside a scrollable card list,
so a book and a technology tagged e.g. `RAG` are easy to spot together.

---

## Deployment

| Target | Command |
|--------|---------|
| Local preview | `cd site && python -m http.server 8000` |
| GitHub Pages | Push `site/` contents to the `gh-pages` branch |
| Netlify | Drag and drop the `site/` folder onto Netlify |

---

## Project layout

```
tech-radar/
├── runner.py           # discovery orchestrator — runs scrapers daily
├── radar.py            # curation CLI — human triage and ring management
├── radar_core.py       # shared library — item schema, dedup, persistence
├── build_site.py       # static site assembler — bundles web/ → site/
├── edit_server.py      # local server — serves web/ with editing turned on
├── scrapers/           # discovery sources — one module per source
│   ├── base.py         # Scraper base class (the discover() contract)
│   ├── github_trending.py
│   ├── reddit.py
│   └── rss_feeds.py    # registered; discover() is still a stub
├── web/                # the browser frontend (served as-is, no build step)
│   ├── index.html      # HTML shell — loads config.js + dashboard.jsx via CDN
│   ├── config.js       # runtime flag — window.RADAR_EDIT (false in the build)
│   ├── dashboard.jsx   # React dashboard — Atlas + Index views + edit mode
│   ├── books.html      # HTML shell for the Reading List — loads books.jsx via CDN
│   ├── books.jsx       # React book radar — Atlas-style radar + scrollable list
│   └── concept-drawings/   # prototype dashboard concepts (dashboard2/3.jsx)
├── tests/              # stdlib unittest suite for radar_core
├── docs/               # routine guides + architecture.html diagram
├── SKILL-manage.md     # Skill definition for Claude-assisted curation
├── data/
│   ├── items/          # one .json file per technology (generated)
│   │   ├── github/
│   │   └── reddit/
│   ├── raw/            # audit trail of raw scrape output (generated)
│   ├── radar.json      # aggregated payload for the dashboard (generated)
│   └── books.json       # hand-curated Reading List — { generated, books: [...] }
└── site/               # deployable static site (generated by build_site.py)
    ├── index.html
    ├── config.js        # window.RADAR_EDIT = false → read-only public build
    ├── dashboard.jsx
    ├── books.html
    ├── books.jsx
    └── data/
        ├── radar.json
        └── books.json
```

---

## Known gaps

| Gap | Status |
|-----|--------|
| `scrapers/rss_feeds.py` | Registered in `runner.py` and conforms to the `Scraper` contract, but `discover()` is still a stub that returns `[]`. Fill it in with `urllib` + `xml.etree` to bring the RSS source online. |
| arXiv source | The `Techniques` quadrant only gets shipped tools, not research. See `TODO.md` for the planned arXiv scraper and the bloat-control decision it requires. |

---

## Suggested weekly workflow

1. `python runner.py` — run discovery (or schedule it via cron)
2. `python radar.py list --ring Discovered` — see what's new
3. For each interesting item: `show`, then `promote` to the right ring
4. Fix wrong quadrants or missing companies: `set`
5. Archive irrelevant or stale tech: `archive`
6. `python build_site.py` — publish the updated dashboard

See `SKILL-manage.md` for Claude-assisted curation instructions.
