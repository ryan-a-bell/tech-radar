# TODO

Planned work for the technology radar. Each item captures enough context to
pick up later without re-deriving the design.

---

## arXiv scraper integration

Add an arXiv source so the `Techniques` quadrant picks up emerging research,
not just shipped tools. Fits the existing `scrapers/base.Scraper` contract.

- **Access:** arXiv public API / Atom feed (`http://export.arxiv.org/api/query`).
  No key, no OAuth. stdlib `urllib` + `xml.etree` is enough — keeps the
  zero-dependency promise.
- **Categories:** start with `cs.AI`, `cs.LG`, `cs.CL`, `cs.SE`. Pull recent
  submissions per category, sorted by submission date.
- **Mapping:** `quadrant="Techniques"`, `momentum` from a recency/heuristic
  signal (arXiv gives no stars), `company=None`, `tags=[category]`. Use the
  abstract (truncated) as the description.
- **Dedup:** papers often link a GitHub repo in the abstract — pass it as
  `linked_url` so the existing `canonical_url` merge collapses the paper and
  the repo into one item.
- **Register:** add `ArxivScraper()` to `SCRAPERS` in `runner.py`.

### Bloat control (decide before shipping)

arXiv (like HN/Lobsters) can flood the inbox with papers that never become
"technologies." Pick one approach so the store doesn't bloat:

- **Way 1 — Promotion-gated persistence (preferred).** Scrapers write to an
  ephemeral `data/inbox/` that's pruned each run (auto-expire uncurated items
  using the staleness logic). Items graduate to the permanent `data/items/`
  only when a human promotes them. Noisy sources become consequence-free
  because their noise auto-expires.
- **Way 2 — Ingest filtering + per-source cap.** Keep one store, but gate
  ingestion: relevance filter (abstract must hit a tech-term allowlist) plus a
  hard cap (`keep top N by momentum per source per run`). Same shape as the
  Reddit `min_score=150` gate, made first-class and configurable.

---

## Semantic similarity heatmap page

A dedicated dashboard view: an N×N grid colored by pairwise similarity between
items, for spotting clusters (e.g. "we have 6 overlapping LLM-agent
frameworks"). Opt-in / phase 2 — build the per-card "Related tech" panel first
since it shares the same data and scales better.

- **Similarity source:** start with BM25 over `name + description + tags`
  (pure stdlib, no deps). Optionally upgrade to embeddings (local
  `sentence-transformers` or an API) later.
- **Precompute, don't compute in-browser.** Attach neighbor/similarity data to
  `radar.json` at build time so the page just renders. Gate behind a flag
  (`build_site.py --with-similarity`) so the published site can ship without
  it.
- **Scale:** the matrix is O(N²) — fine at ~150 items (~23k cells), unreadable
  at 1,000+. Render over a filtered subset (one quadrant at a time, or
  "similarity above X only") or over cluster representatives rather than every
  raw item.

---

## Backlog (from brainstorm, not yet scheduled)

- Per-card "Related tech" panel (foundation for the heatmap above).
- Test suite (stdlib `unittest`) for dedup, `canonical_url`, `star_trend`.
- Scheduled discovery via GitHub Actions + auto-deploy to Pages.
- Curation history/audit log per item.
- Move hardcoded scraper config (subs, feeds, limits) into `sources.toml`.
- Expand `canonical_url` dedup beyond GitHub (package registries, project
  domains).
- Hacker News + Lobsters scrapers (low-friction, key-free).
