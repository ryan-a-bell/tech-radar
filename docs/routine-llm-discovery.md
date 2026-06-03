# LLM Organic Discovery Routine

A Claude Routine that uses web browsing to discover emerging technologies
across a broad set of sources. Unlike the rule-based scrapers in `runner.py`
(which parse specific HTML structures), this routine reads sources the way a
human would — understanding context, filtering noise, and extracting signal.

Run this weekly, or on a schedule that complements the daily `runner.py` routine.

## What it does differently from runner.py

| | runner.py scrapers | This routine |
|---|---|---|
| Approach | Parse fixed HTML/JSON endpoints | Browse and read like a human |
| Sources | GitHub Trending, Reddit, RSS stubs | HN, Product Hunt, tech press, blogs |
| Noise filtering | Score/star thresholds | LLM judgment |
| Breaks when | Page HTML changes | Rarely — reads meaning not structure |
| Speed | Fast (~10s) | Slower (~2–5 min) |
| Frequency | Daily | Weekly |

Both routines write to the same `data/items/` store and dedup correctly —
running both means broader coverage with no duplicates.

## Setup

1. Go to [claude.ai/code/routines](https://claude.ai/code/routines) → **New routine**
2. **Name:** `Tech Radar — Weekly LLM Discovery`
3. **Prompt:** paste the block below exactly
4. **Repository:** `ryan-a-bell/tech-radar`
5. **Environment:** set Network access to **Full** (the routine needs to browse
   arbitrary URLs — tech news sites, HN, Product Hunt, etc.)
6. **Trigger:** Schedule → Weekly (e.g. Monday 07:00)
7. Click **Create**

## Routine prompt

```
You are running the weekly organic discovery pass for a technology radar.
Your job is to browse tech sources, identify genuinely new and interesting
technologies, and add any that are not already tracked to the radar.

─── SOURCES TO CHECK ───────────────────────────────────────────────────────

Browse each of these in order. You do not need to exhaust every link —
aim for depth on the most signal-rich pages, not breadth at the expense
of quality.

1. Hacker News front page and "Show HN" posts from the past 7 days
   https://news.ycombinator.com
   https://news.ycombinator.com/show
2. GitHub Trending (all languages, past week)
   https://github.com/trending?since=weekly
3. Product Hunt — top products this week
   https://www.producthunt.com
4. The New Stack — recent articles
   https://thenewstack.io
5. InfoQ — news and articles
   https://www.infoq.com

─── WHAT COUNTS AS A TECHNOLOGY ────────────────────────────────────────────

Add it if it is a concrete, usable thing: a language, runtime, framework,
tool, platform, library, or technique that a software team could adopt.

Skip it if it is:
- A blog post, tutorial, or opinion piece about an existing technology
- A product announcement with no public release (vaporware)
- A company or service, not a technology (e.g. "Stripe" — skip; "Stripe
  Elements" as a technique — consider)
- Already well-established (e.g. React, Kubernetes, Python) — the radar
  tracks *emerging* things
- A duplicate of something already in data/radar.json (check first)

─── DEDUP CHECK ─────────────────────────────────────────────────────────────

Before adding anything, check whether it is already tracked:

  python runner.py --build 2>/dev/null  # ensures radar.json is current
  python radar.py find "<name>"

If radar.py find returns a result, skip that technology.

─── DATA MODEL ──────────────────────────────────────────────────────────────

Each new technology maps to these fields. Be conservative — if you are
unsure of a value, use the defaults shown.

  name        Short, recognisable name (e.g. "Bun", "Zig", "Temporal")
  description One clear sentence: what it is and why it matters. No hype.
  quadrant    One of: Techniques | Tools | Platforms | Languages
                Techniques  — approaches, patterns, methodologies
                Tools       — CLIs, editors, build systems, testing tools
                Platforms   — clouds, runtimes, databases, infra you deploy on
                Languages   — programming/query/config languages
  ring        Always "Discovered" — humans classify later
  source      A short label for where you found it, e.g. "HackerNews",
              "ProductHunt", "GitHub", "TheNewStack"
  url         The primary URL (project site, GitHub repo, or article)
  company     Vendor name if it is a company product (e.g. "Vercel").
              None / omit for open-source community projects.
  momentum    0–100 integer. Use HN points ÷ 10, GitHub stars gained ÷ 10,
              or your best estimate of current interest. Cap at 100.
  tags        List of short topic tags, e.g. ["wasm", "edge", "runtime"]

─── HOW TO ADD EACH TECHNOLOGY ──────────────────────────────────────────────

For each technology you decide to add, run this Python snippet (fill in
the values; omit company if None):

  python3 - <<'PYEOF'
  import sys; sys.path.insert(0, '.')
  import radar_core as core

  item = core.new_item(
      source="<source>",
      key="<url-slug-or-unique-key>",
      name="<name>",
      description="<description>",
      url="<url>",
      quadrant="<quadrant>",
      momentum=<momentum>,
      tags=<tags>,
      company="<company-or-omit>",
  )
  saved = core.save_new(item)
  print("saved" if saved else "already exists — skipped")
  PYEOF

─── FINISHING UP ────────────────────────────────────────────────────────────

After you have processed all sources and added any new technologies:

1. Run `python runner.py --build` to regenerate data/radar.json.
2. Check how many new items you added:
     python radar.py list --ring Discovered
3. If you added anything, stage and commit:
     git add data/items/ data/radar.json
     git commit -m "llm-discovery: YYYY-MM-DD — N new technologies"
     git push
4. If you added nothing, exit cleanly with no commit.

─── DONE ────────────────────────────────────────────────────────────────────

A successful run ends with either:
- A pushed commit listing the new technologies in the message, or
- A clear statement that nothing new was found this week.

Do not commit partial state. Do not modify any item that already exists.
```

## Tuning tips

- **Too much noise?** Raise the implicit momentum bar — in the prompt, add
  "Only add technologies with momentum ≥ 30" before the finishing-up section.
- **Missing sources?** Add URLs to the SOURCES TO CHECK section. The routine
  reads them like a human, so any public page works.
- **Wrong quadrant guesses?** After the routine runs, use `/project:radar-manage`
  to fix classifications: `python radar.py set "<name>" quadrant Platforms`.
- **Network errors on specific sites?** Some sites block cloud IP ranges. If a
  source consistently fails, remove it from the prompt and add an alternative.
