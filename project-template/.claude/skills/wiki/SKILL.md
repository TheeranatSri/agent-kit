---
name: wiki
description: Use to add, find or check project knowledge in the wiki folder (index.md + log.md + pages). Triggers - "wiki", "จดไว้ใน wiki", "บันทึก decision", "หาใน wiki", "wiki lint", a new result / decision / lesson / plan to record.
---

# Project knowledge wiki

One folder (`wikiDir` in `.claude/handoff.json`, default `notebooks/knowledge`) holds the project's decisions,
results, plans and lessons as Markdown pages. Two files keep it findable at low token cost:

- `index.md`: the catalogue, one line per page: `- [Title](page.md) — <type> · <status> · <question it answers>`,
  grouped under `## ` headings. Agents read it first and follow links instead of searching the folder.
- `log.md`: append-only events, oldest first: `## [YYYY-MM-DD] <ingest|result|decision|lesson|plan> | <title>`
  + 1-2 lines with the page link and commit hash. Never edit old entries.

Every page starts with frontmatter: `type`, `status` (active | reference | done | superseded), `updated`
(last content change, YYYY-MM-DD), `sources` (data paths / commits, may be `[]`); a superseded page also has
`superseded_by: <page.md>`.

## Query (find something)

1. Read `index.md`; pick pages by their question. Skip `superseded` pages, use the `superseded_by` page.
2. Read only the pages you need. If nothing fits, say so; do not grep the whole folder first.

## Ingest (record new knowledge)

1. New topic → new page with frontmatter; an existing topic → edit that page and bump `updated`.
   Keep page bodies as written; do not rewrite history to tidy it.
2. New or renamed page → its line in `index.md`. Status change → frontmatter `status` + the index line.
3. Knowledge event (new data / result / user decision / lesson / plan) → one entry at the end of `log.md`.
   Tooling or formatting changes get no log entry.
4. Commit the page, `index.md` and `log.md` together (one commit); put the hash in the log entry when known,
   else in the next entry.

## Lint (check, zero LLM cost)

```bash
python3 .claude/skills/wiki/wiki_lint.py            # reads wikiDir from .claude/handoff.json
python3 .claude/skills/wiki/wiki_lint.py --dir docs/knowledge
```

Errors (exit 1): missing frontmatter keys, unknown status, superseded without a valid `superseded_by`, a page not
in `index.md`, an index link to a missing file, an index status that differs from the page, a malformed or
out-of-order `log.md` heading. Fix them, then run it again; report the result as a `Check:` line.
