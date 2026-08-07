---
name: "source-command-conference-track"
description: "Check tracked conferences (INCOSE IS, RAMS, …) for new or updated year-over-year editions and record them in the Learning Library. Fetches each conference's site, extracts the next edition's dates/location/CFP deadline, and writes it via learning.py edition."
---

# source-command-conference-track

Use this skill when the user asks to run the migrated source command
`conference-track`, or asks to check/refresh recurring conferences (INCOSE IS,
RAMS, and any other `type: conference` items in the Learning Library) for newly
announced or changed year-over-year editions. For adding a brand-new conference
to track, rating, or changing a personal attendance status, use
`learning-manage`; for technologies/tools, use `radar-manage`.

## Command Template

# Conference Tracking — Scrape Updates

Conferences live in the **Learning Library** as `type: conference` items.
Unlike a book or a video, a conference **recurs**: one `learning/<id>.md` holds
the whole series and a list of `editions`, one per year
(`year | dates | location | status | cfp | url`). This skill is the "scraper"
for that list — it visits each tracked conference's website, reads off the next
occurrence, and records it. Extraction is done by **reading** the page (via
WebFetch/WebSearch), not by brittle HTML parsing, because every conference site
is laid out differently.

## What it updates

Only the **factual** fields of an edition — `dates`, `location`, `cfp`, and the
edition `url`. It creates a new edition (status `Announced`) when a future year
is announced that isn't recorded yet. Never overwrite a personal edition status
(`Interested` / `Registered` / `Attended` / `Skipped`) — leave `--status` off
unless the edition is brand new. Never invent a date or venue: if a page
doesn't state it, leave the field blank.

## Procedure

1. Pick targets — `python learning.py list --type conference` for a sweep, or
   resolve one by name. Read its url + recorded editions with
   `python learning.py show <id-or-name>`.
2. Fetch and read each site with WebFetch, asking for the next edition's year,
   exact dates, host city/venue, and CFP / abstract deadline. Follow the
   homepage's link to the year-specific event or "call for papers" page.
   - On a 403 / bot wall / JS-only shell (e.g. INCOSE's site), fall back to
     WebSearch for `"<conference> <next-year> dates location call for papers"`
     and read the official result; cross-check year + organizer.
   - Report only what the source states.
3. Diff against the recorded editions: add a year not on file; update
   `dates` / `location` / `cfp` that changed; skip unchanged ones silently.
4. Record with the CLI (writes the `.md` and rebuilds `data/learning.json`):
   ```bash
   python learning.py edition <id> --year 2028 \
     --dates "2028-01-25..01-28" --location "City, ST (Venue)" \
     --cfp "abstracts 2027-04-30" --status Announced   # new future edition
   python learning.py edition <id> --year 2027 \
     --location "St. Petersburg, FL" --cfp "draft papers 2027-07-31"  # fix facts
   ```
   Editions are keyed by `--year` (upsert, not duplicate). `--location` has a
   `--loc` alias. Dates are free text; prefer `YYYY-MM-DD..MM-DD`.
5. Summarize what actually changed. If a site was unreachable and search
   confirmed nothing, say so rather than guessing.

## Adding a conference to the tracked set

```bash
python learning.py add "<Full Conference Name>" --type conference \
  --author "<organizer>" --url "<homepage>" --topics "Skills" \
  --status Queued --blurb "<one honest sentence on what it is>"
python learning.py edition "<name>" --year 2026 --dates "..." --location "..."
```

## Notes

- Topics use the shared vocabulary (AI, ML, Agents, Skills, Prompts, Trading,
  Quant, RAG, Data Feeds); most professional conferences map to `Skills`.
- Source of truth is `learning/<id>.md`; the CLI rebuilds `data/learning.json`.
  Hand-edited an edition line? Run `python build_learning.py`. Edition line
  format + the edition status vocabulary are documented in `learning/README.md`.
- Discovers/records dates only — deciding to attend (moving an edition to
  `Registered` / `Attended`) is a human call via `learning-manage`.
