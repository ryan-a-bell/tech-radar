# People

People and their skills, tracked in Markdown and mapped against the technology
radar — the same idea as `projects/`, with the noun swapped. This directory is
kept **separate** from `data/` (scraped tech) and `projects/` (personal work):
people are hand-written profiles, not generated output.

`build_people.py` reads every `*.md` here (except this README), resolves each
person's declared `skills` against the radar, and writes `data/people.json`,
which the **PEOPLE** tab (`web/people.html`) renders.

An entry can also be an **organization** rather than a person — a company or
vendor you keep a contact card for — via `kind: org`. See
[Organization contacts](#organization-contacts-kind-org) below.

## What it's for (hybrid framing)

A person carries both what they can do **today** (`skills`) and what they want
to grow **into** (`interests`). That powers three cross-links, all computed in
the browser from the same recommender the Projects page uses:

- **Recommend tech** — tools a person should check out. Semantic match of their
  bio + interests against tool descriptions, plus *peer* tools that similar
  people already know. Growth `interests` bias it toward new ground, not more
  of the same.
- **Matching projects** — staffing. Projects whose declared stack overlaps a
  person's skills, and whose prose is semantically close to their bio.
- **Similar people** — who to ask about X; skill kinship for the Map view.

## File format

Each person is one Markdown file: a YAML-style front-matter block between `---`
fences, followed by a free-text bio.

```markdown
---
id: ryan-bell                     # unique slug (defaults to the filename)
name: Ryan Bell                   # display name
role: Quant Developer             # free-form job title
topics: [Quant, Trading]          # current focus — from the radar's TOPICS vocab
interests: [Agents, ML]           # growth areas — also from TOPICS
skills: [gs-quant, Python, options pricing]   # what they know

# --- contact block (all optional; the rolodex card) ---
organization: Meridian Systematic # where they work
business: Systematic trading desk — derivatives market-making   # their line of work
location: Chicago, IL · CT (UTC-6)
relationship: Colleague           # Self / Colleague / Collaborator / Contractor / …
how_met: Same desk since 2024     # free-text
email: ryan.bell@example.com
phone: +1 (312) 555-0142
website: ryanbell.dev             # bare domain — expanded to a URL in the browser
github: ryan-a-bell               # bare handle
linkedin: ryanabell               # bare handle
x: ryan_quant                     # bare handle
last_contact: 2026-08-01          # ISO date; shown as "N days ago"
notes:                            # block list; each line optionally dated
  - 2026-08-01: Wants to hand generate-and-test to agents.
  - Undated notes are fine too.
---

Everything below the closing fence is the bio. This prose is what the semantic
recommender reads, so describe what the person works on and the problems they
solve — that is what gets matched against tool descriptions and project prose.
```

### Contact block — the rolodex fields

Every key above the bio except `id`/`name`/`role`/`topics`/`interests`/`skills`
is **optional** and purely additive: it feeds the profile card, never the
recommender. Add as much or as little as you have.

- **`organization`, `business`, `location`, `relationship`, `how_met`,
  `email`, `phone`** — plain scalars. `business` is *what that organization
  does* / their line of work, distinct from their personal `role`.
- **`website`, `github`, `linkedin`, `x`** — stored as bare handles or a bare
  domain; the page expands them to full URLs, so write `ryan-a-bell`, not the
  whole GitHub link.
- **`last_contact`** — an ISO `YYYY-MM-DD` date, rendered with a relative
  "N days ago".
- **`notes`** — a block list of free-text lines. Prefix a line with
  `YYYY-MM-DD:` to date it and it renders as a dated log entry; undated lines
  are kept as-is.

Because this is contact information for real people, keep the repo **private**
if you fill it in — nothing here is meant to be published.

## Organization contacts (`kind: org`)

Sometimes you want a contact card for an **organization** — a company, vendor,
or team — not an individual. Add `kind: org` to the front-matter and the entry
becomes an org contact. It lives in this same folder and is managed the same
way; only the card changes.

```markdown
---
id: meridian-systematic
name: Meridian Systematic        # the org's name IS the entry name
kind: org                        # org | organization | company all work
topics: [Quant, Trading]
business: Systematic trading firm — derivatives market-making
location: Chicago, IL
email: contact@meridian-sys.example
phone: +1 (312) 555-0100
website: meridian-sys.example
linkedin: company/meridian-systematic   # a slash → used as a full path (company page)
last_contact: 2026-08-04
notes:
  - 2026-08-04: Renewal window is Q4.
---

The bio describes the organization.
```

An org reuses the **entire** contact block above — `role`, `interests`, and
`skills` are simply omitted (a `skills:` list, if present, renders as the org's
"Stack / focus"). Two behaviours make the org a hub:

- **People here** — the org card auto-lists every *person* entry whose
  `organization` matches the org's `name` (case-insensitive). Fill in
  `organization: Meridian Systematic` on a person and they appear under the org.
- **Org link** — on a person's card, that `organization` name becomes a link to
  the org entry when one exists.

Because an org is a contact record and not a teammate, org entries are kept out
of the people-only analytics: the similarity **Map**, the bus-factor **Skills**
view, and the "similar people" recommendation. They still appear in the board
list and under an **Organization** filter chip.

### `skills` — radar tools *and* free-form

A skill entry is matched against the radar by id (`manual:gs-quant`) or exact
name (`gs-quant`). Entries that resolve become **radar-backed skills** — they
link to the tool, carry its quadrant colour, and feed the tech recommender's
peer ranking, the staffing overlap, and the bus-factor Skills view. Entries
that don't resolve (`Python`, `options pricing`, `LangGraph`) are kept as
**free-form skills** — displayed as neutral tags, still searchable, just not
linked to a radar item. Free-form skills are expected and normal, not an error.

`topics` and `interests` both draw from the same `TOPICS` vocabulary as the
tech radar, Learning Library, and Projects — so a person, a project, a book,
and a technology can all share a topic tag.
