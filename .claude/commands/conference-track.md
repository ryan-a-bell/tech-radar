---
description: Check tracked conferences (INCOSE IS, RAMS, …) for new or updated year-over-year editions and record them in the Learning Library. Fetches each conference's site, extracts the next edition's dates/location/CFP deadline, and writes it via learning.py edition.
---

# Conference Tracking — Scrape Updates

Conferences live in the **Learning Library** as `type: conference` items (see
`learning-manage`). Unlike a book or a video, a conference **recurs**: one
`learning/<id>.md` holds the whole series and a list of `editions`, one per
year (`year | dates | location | status | cfp | url`). This skill is the
"scraper" for that list — it visits each tracked conference's website, reads
off the next occurrence, and records it. Extraction is done by reading the
page (via WebFetch), **not** by brittle HTML parsing, because every conference
site is laid out differently.

Use this when the user says: "check my conferences for updates", "any new
INCOSE / RAMS dates?", "refresh the conference editions", or "when's the next
<conference>". For adding a brand-new conference to track, or changing a
personal attendance status, use `learning-manage`.

## What it updates

Only the **factual** fields of an edition — `dates`, `location`, `cfp`, and the
edition `url`. It creates a new edition (status `Announced`) when a future year
is announced that isn't recorded yet. It must **never** overwrite a personal
edition status the user set (`Interested` / `Registered` / `Attended` /
`Skipped`) — leave `--status` off unless the edition is brand new or the user
asks. And it must **never invent** a date or venue: if a page doesn't state it,
leave the field blank (`dates TBD` is fine).

## Procedure

1. **Pick the targets.** For a sweep, list what's tracked:
   ```bash
   python learning.py list --type conference
   ```
   For one conference, resolve it by name/id. Get its homepage and the
   editions already on file:
   ```bash
   python learning.py show <id-or-name>      # JSON: url, editions[]
   ```

2. **Fetch and read each site.** WebFetch the conference `url`, asking for the
   next edition's **year, exact dates, host city/venue, and the
   call-for-papers / abstract-submission deadline**. Conference homepages often
   redirect to a year-specific event page or a "call for papers" page — follow
   the relevant link and fetch that too.
   - If WebFetch returns 403 / a bot wall / a JS-only shell (INCOSE's site does
     this), fall back to **WebSearch** for `"<conference> <next-year> dates
     location call for papers"` and read the official result. Cross-check the
     year and organizer so you don't record another event's dates.
   - Report only what the source actually states.

3. **Diff against what's on file.** For each conference, compare the fetched
   facts to the recorded `editions`:
   - A **year not on file** → add it.
   - A recorded edition whose `dates` / `location` / `cfp` **changed** (e.g.
     RAMS moving venue, a CFP deadline extended) → update those fields.
   - No change → skip it silently.

4. **Record it** with the CLI (writes the `.md` and rebuilds
   `data/learning.json` in one step):
   ```bash
   # a newly announced future edition
   python learning.py edition <id> --year 2028 \
     --dates "2028-01-25..01-28" --location "City, ST (Venue)" \
     --cfp "abstracts 2027-04-30" --status Announced

   # correcting facts on an existing edition (note: no --status)
   python learning.py edition <id> --year 2027 \
     --location "St. Petersburg, FL (Hilton Bayfront)" \
     --cfp "draft papers 2027-07-31"
   ```
   Dates are free text — prefer `YYYY-MM-DD..MM-DD`. `--location` accepts a
   `--loc` alias. Editions are keyed by `--year`, so re-running is an upsert,
   not a duplicate.

5. **Summarize.** Tell the user what actually changed — "INCOSE IS 2028
   announced: 18–23 June, location TBD; RAMS 2027 CFP draft-paper deadline now
   31 Jul 2027" — not just "done". If a site was unreachable and search didn't
   confirm anything, say so rather than guessing.

## Adding a conference to the tracked set

If the user wants to start tracking a new one, add the series first (read the
site and write a real one-sentence blurb), then seed its known editions:

```bash
python learning.py add "<Full Conference Name>" --type conference \
  --author "<organizer>" --url "<homepage>" --topics "Skills" \
  --status Queued --blurb "<one honest sentence on what it is>"
python learning.py edition "<name>" --year 2026 --dates "..." --location "..."
```

## Notes

- Topics use the shared vocabulary (**AI, ML, Agents, Skills, Prompts, Trading,
  Quant, RAG, Data Feeds**); most professional conferences map to `Skills`.
- The source of truth is `learning/<id>.md`. The CLI rebuilds
  `data/learning.json`; if you ever hand-edit an edition line, run
  `python build_learning.py` to republish. Edition line format and the edition
  status vocabulary are documented in `learning/README.md`.
- This skill discovers/records dates only — deciding to attend (moving an
  edition to `Registered` / `Attended`) is a human call via `learning-manage`.
