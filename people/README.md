# People

People and their skills, tracked in Markdown and mapped against the technology
radar — the same idea as `projects/`, with the noun swapped. This directory is
kept **separate** from `data/` (scraped tech) and `projects/` (personal work):
people are hand-written profiles, not generated output.

`build_people.py` reads every `*.md` here (except this README), resolves each
person's declared `skills` against the radar, and writes `data/people.json`,
which the **PEOPLE** tab (`web/people.html`) renders.

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
---

Everything below the closing fence is the bio. This prose is what the semantic
recommender reads, so describe what the person works on and the problems they
solve — that is what gets matched against tool descriptions and project prose.
```

### `skills` — radar tools *and* free-form

A skill entry is matched against the radar by id (`manual:gs-quant`) or exact
name (`gs-quant`). Entries that resolve become **radar-backed skills** — they
link to the tool, carry its quadrant colour, and feed the tech recommender's
peer ranking, the staffing overlap, and the bus-factor Skills view. Entries
that don't resolve (`Python`, `options pricing`, `LangGraph`) are kept as
**free-form skills** — displayed as neutral tags, still searchable, just not
linked to a radar item. Free-form skills are expected and normal, not an error.

`topics` and `interests` both draw from the same `TOPICS` vocabulary as the
tech radar, Reading List, and Projects — so a person, a project, a book, and a
technology can all share a topic tag.
