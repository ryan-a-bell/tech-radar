# Daily Discovery Routine

A Claude Routine that runs the tech radar discovery pipeline every day on
Anthropic-managed cloud infrastructure. No server required — runs while your
laptop is closed.

## What it does

1. Runs `python runner.py` against the repo
2. Scrapes GitHub Trending, Reddit, and RSS feeds (RSS is a stub until implemented)
3. Deduplicates across sources using canonical GitHub URLs
4. If anything new was found, commits `data/items/` and `data/radar.json` and pushes to main
5. If nothing new was found, exits cleanly with no commit

Human-curated fields (`ring`, `quadrant`, `company`) are never touched by the runner.
After the routine runs, open a Claude Code session and type `/project:radar-manage`
to triage the new `Discovered` items.

## Setup

1. Go to [claude.ai/code/routines](https://claude.ai/code/routines)
2. Click **New routine**
3. **Name:** `Tech Radar — Daily Discovery`
4. **Prompt:** paste the block below exactly
5. **Repository:** `ryan-a-bell/tech-radar`
6. **Trigger:** Schedule → Daily (pick a time outside business hours, e.g. 06:00)
7. Click **Create**

To test immediately: open the routine and click **Run now**.

## Routine prompt

```
Run the daily tech radar discovery pipeline.

Steps:
1. Run `python runner.py` and capture its output.
2. Read the "totals:" line in the output to find the count of new and
   cross-source-merged discoveries, e.g.:
     "--- totals: 4 new, 18 known, 2 cross-source merges, 0 scraper errors"
3. If new > 0 or cross-source merges > 0:
   a. Stage data/items/ and data/radar.json.
   b. Commit with the message:
        discovery: YYYY-MM-DD — N new, M merged
      where YYYY-MM-DD is today's date and N/M are the actual counts.
   c. Push the commit to the main branch.
4. If new == 0 and merges == 0, do nothing — no commit needed.

Rules:
- Do not modify any item's ring, quadrant, company, or other human-curated field.
- Individual scraper failures printed by runner.py are expected and non-fatal;
  proceed with the items that did succeed.
- If runner.py itself fails to start (import error, missing file), report
  the error in a comment and stop — do not commit partial state.
```

## After a routine run

- Open the run from [claude.ai/code/routines](https://claude.ai/code/routines) to see the transcript
- A green status means the session ran without an infrastructure error — open
  the transcript to confirm what was actually discovered and committed
- New items land in the `Discovered` ring; triage them with `/project:radar-manage`
- Once curated, run `python build_site.py` locally and push `site/` to deploy
