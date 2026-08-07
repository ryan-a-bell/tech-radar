---
description: Manage and classify items in the technology radar — promote/demote between rings, set quadrant or company, archive stale tech, list the review queue, or search the radar.
---

# Tech Radar — Management

The scraper discovers tech and parks it in the **Discovered** ring. This
skill is the human side: triaging that queue and curating the radar. All
changes go through `radar.py`, which edits the per-tech JSON files and
rebuilds `data/radar.json` for the dashboard automatically.

## The rings

| Ring | Meaning |
|------|---------|
| Discovered | Found by a scraper, not yet reviewed (the inbox) |
| Assess | Worth a closer look / experiment |
| Trial | Actively trying it on real work |
| Adopted | Recommended default |
| Archived | Retired / dead / irrelevant — kept (dated) so it won't re-surface |

Only a human moves items out of Discovered. Scrapers never classify.

## Topics

Items also carry a curated `topics` list — a controlled vocabulary,
separate from the free-form `tags` scrapers emit. Valid topics: **AI, ML,
Agents, Skills, Prompts, Trading, Quant, RAG** (extend the `TOPICS` list in
`radar_core.py`). Assign with `set <item> topics "AI,Agents"` and filter the
dashboard or `list --topic Agents`.

## Commands

```bash
python radar.py list                      # everything, grouped by ring
python radar.py list --ring Discovered     # just the review queue
python radar.py list --topic Agents        # items tagged with a topic
python radar.py list --ring Archived --older-than 90   # stale archives
python radar.py show <id-or-name>          # full JSON for one item
python radar.py find <text>                # search name + description

python radar.py promote <id-or-name> Trial # classify into a ring
python radar.py demote <id-or-name>         # send back to Discovered
python radar.py set <id-or-name> quadrant Platforms
python radar.py set <id-or-name> company "Anthropic"
python radar.py set <id-or-name> topics "AI,Agents"   # curated topics
python radar.py archive <id-or-name>        # move to Archived (dated)

python radar.py add "<Name>" --url <url> --quadrant <quadrant> \
  --description "<summary>" [--company <vendor>] [--momentum N]  # manually add
```

Items can be named by exact id (`github:oven-sh/bun`), exact name
(`Bun`), or a unique partial name (`uv`). Ambiguous partials are
rejected with the list of matches.

## Adding a technology by hand

`add` is for tech the user names directly rather than something a scraper
found — e.g. "add this GitHub repo to Assess." Before running `add`, actually
go check the source: open the URL (README, docs site, package page — whatever
`show`/`find` would have surfaced for a scraped item) and read enough to
understand what it is and does. Do not add an item with a placeholder or
empty `--description`.

1. Fetch and read the source (repo README, docs, landing page).
2. Write a real one-to-two sentence `--description` summarizing what it is
   and why it's relevant to the radar (not a copy-pasted tagline).
3. Set `--quadrant` (`Techniques`, `Tools`, `Platforms`, `Languages`) and
   `--company` if there's a vendor behind it.
4. Run `add`, then `promote <item> <Ring>` to put it directly into the ring
   the user asked for (`add` alone lands in Discovered by default — confirm
   with `show` and promote if needed).
5. Tell the user what you found, in a short summary, not just that the item
   was added.

## Typical review session

1. `python radar.py list --ring Discovered` — see what's new.
2. For each item: `show` it, decide, then `promote` / `archive`.
3. Fix any wrong `quadrant` or missing `company` with `set`.
4. Done — `radar.json` was rebuilt after every change, so just
   refresh the dashboard.

## Notes

- `company` is the vendor behind a product (e.g. "Vercel"); leave it
  unset for community or individual projects. GitHub items from known
  orgs get it auto-filled by the scraper.
- `archive` is for tech that's dead or irrelevant — it moves to the
  Archived ring (stamped with `archived_at`) so it won't be re-surfaced as
  a new discovery, and the graveyard can be filtered by age (`--older-than`).
- Never edit the JSON files by hand while the runner might be active;
  use these commands so changes are atomic and the rebuild stays in sync.
