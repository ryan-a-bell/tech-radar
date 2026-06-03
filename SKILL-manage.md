---
name: tech-radar-manage
description: Use this skill to manage and classify items in a technology radar — promoting items between rings (Discovered, Assess, Trial, Adopt, Hold), demoting them back to review, setting an item's quadrant or company, archiving stale tech, listing the review queue, or searching the radar. Use whenever the user wants to triage what their scrapers discovered, change an item's classification, or curate the radar. Pairs with the tech-radar-scraper skill, which handles discovery.
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
| Adopt | Recommended default |
| Hold | Avoid / deprecated / not now |

Only a human moves items out of Discovered. Scrapers never classify.

## Commands

```bash
python radar.py list                      # everything, grouped by ring
python radar.py list --ring Discovered     # just the review queue
python radar.py show <id-or-name>          # full JSON for one item
python radar.py find <text>                # search name + description

python radar.py promote <id-or-name> Trial # classify into a ring
python radar.py demote <id-or-name>         # send back to Discovered
python radar.py set <id-or-name> quadrant Platforms
python radar.py set <id-or-name> company "Anthropic"
python radar.py archive <id-or-name>        # Hold + 'archived' tag
```

Items can be named by exact id (`github:oven-sh/bun`), exact name
(`Bun`), or a unique partial name (`uv`). Ambiguous partials are
rejected with the list of matches.

## Typical weekly review

1. `python radar.py list --ring Discovered` — see what's new.
2. For each item: `show` it, decide, then `promote` / `archive`.
3. Fix any wrong `quadrant` or missing `company` with `set`.
4. Done — `radar.json` was rebuilt after every change, so just
   refresh the dashboard.

## Notes

- `company` is the vendor behind a product (e.g. "Vercel"); leave it
  unset for community or individual projects. GitHub items from known
  orgs get it auto-filled by the scraper.
- `archive` is for tech that's dead or irrelevant — it stays on the
  radar in Hold so it won't be re-surfaced as a new discovery.
- Never edit the JSON files by hand while the runner might be active;
  use these commands so changes are atomic and the rebuild stays in sync.
