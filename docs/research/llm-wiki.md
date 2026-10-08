# LLM wiki: findings (2026-10-08)

## 1. Sources
| Title | Author | Date | URL | What it says |
|---|---|---|---|---|
| "LLM Wiki" (gist, an "idea file") | Andrej Karpathy | 2026-04-04 | https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f | The origin. Instead of RAG re-deriving answers each query, an LLM incrementally builds and maintains a persistent, interlinked markdown wiki. Three layers (raw / wiki / schema), three operations (ingest / query / lint), two special files (index.md, log.md). Read only the first 100k of 136k chars of the page (rest = comments, unread). |
| llmwiki (Python CLI "wiki") | koolkhel | date unverified | https://github.com/koolkhel/llmwiki | Deterministic bookkeeper CLI + Claude Code/Kimi as the "brain", Obsidian as viewer. `raw/`, `wiki/`, `AGENTS.md`, generated `index.md`/`log.md`. Commands init, add-source, search, lint, upgrade, timeline. `/wiki-ingest`, `/wiki-query`, `/wiki-lint` in `.claude/commands/`. Permissions stop the agent editing `raw/`, `index.md`, `log.md`. |
| LLM-Wiki Obsidian Setup Guide | kennyg (gist) | last active 2026-10-05 (per fetch) | https://gist.github.com/kennyg/6c45cace2e1c4e424a28fcd51dd6c25b | Layout `index.md, log.md, overview.md, sources/, entities/, concepts/, synthesis/`. Frontmatter `type`, `date_updated`, optional `source_count`, `confidence`. CLAUDE.md rules: never modify raw; always update index+log; keep source summaries factual; flag contradictions, do not overwrite silently. |
| Setup for my Obsidian as LLM knowledge base via Claude Code | mhmzdev (gist) | unverified | https://gist.github.com/mhmzdev/631349438f3efa754fc667accaee4123 | Search hit only, not fetched. |
| What Is Karpathy's LLM Wiki? A Zettelkasten User's Honest Review | WenHao Yu | 2026-04-10 | https://yu-wenhao.com/en/blog/karpathy-zettelkasten-comparison/ | Criticism: container-boundary problem (which page does a source merge into), model collapse from repeated LLM rewriting (no long-term proof), "vibe thinking" (people skip the understanding step). |
| Other write-ups (search hits, not fetched, content unverified) | various | - | https://denser.ai/blog/llm-wiki-karpathy-knowledge-base/ ; https://blog.starmorph.com/blog/karpathy-llm-wiki-knowledge-base-guide ; https://pub.towardsai.net/i-built-karpathys-llm-wiki-twice-once-as-code-once-as-a-md-heres-what-each-one-gives-up-08b31170999a ; https://alirezarezvani.github.io/claude-skills/skills/engineering/llm-wiki/ ; https://community.obsidian.md/plugins/auto-llm-wiki | A search snippet says the gist passed 5,000 stars / 4,000 forks in two weeks (unverified, from a secondary source). |

## 2. The pattern
- Layers: (1) raw sources, immutable, human-curated; (2) wiki, LLM-owned markdown (summaries, entity pages, concept pages, analyses); (3) schema file (CLAUDE.md / AGENTS.md) = contract between human and LLM.
- Special files: `index.md` = content catalog by category, one line per page, updated on every ingest; the LLM reads it first when querying (works at ~100 sources / hundreds of pages, no vector search needed). `log.md` = append-only, prefix like `## [2026-04-02] ingest | Title`, greppable.
- Page types (community convention, not in the gist's text I read): source-summary, entity, concept, synthesis, overview. Frontmatter `type`, dates, `confidence`; `[[wikilinks]]`.
- Operations: Ingest (read a source, discuss, write summary, update index, touch ~10-15 related pages, append log). Query (read index, drill into pages, answer with citations; good answers are filed back as pages). Lint (periodic: contradictions, stale claims, orphans, missing cross-links, data gaps).
- Who edits: human curates sources, asks questions, thinks; LLM does all bookkeeping and writes the wiki. Optional tools: Obsidian (viewer, graph, Web Clipper, Dataview), qmd (local BM25/vector search) when the index stops being enough.
- Pitfalls: model collapse by repeated rewriting; page-boundary decisions; false confidence in synthesized pages; humans outsourcing understanding; cost of touching 10-15 pages per ingest.
- With Claude Code: schema in CLAUDE.md, slash commands/skills for ingest/query/lint, permission deny rules on `raw/` + generated files, a CLI for deterministic parts (link check, index/log generation).

## 3. Fit with notebooks/knowledge/
Present now: backlog.md (B1-B21 table), lessons.md (P1-P9, Problem/Cause/Fix/Prevent/Seen), session-log-2026-10-06.md and -10-08.md (Status/Done/Decisions/Open), topic notes (canonical-prompt-experiment.md: Decisions / Measurements / Open; prompt-v3-results.md, bu-prompt-spec.md, bu-framework-survey.md, deterministic-cdt-plan.md, brand-signal-experiments.md), bu-identity/ (README + per-BU notes), plus semantic/ (BQ YAML + README + HANDOFF), structured lines, /handoff skill, and the CLAUDE.md "read lessons first" rule.

| Pattern part | Status here |
|---|---|
| Schema file | Exists (CLAUDE.md, user CLAUDE.md), but has no wiki-page conventions |
| Raw sources | Partly: data/ (work files), semantic/metadata, BQ; no immutable "sources" notes for external docs/papers; data/work is outside the knowledge folder |
| Wiki pages | Topic notes exist, flat, no type/frontmatter, little cross-linking |
| log.md | Equivalent = per-day session logs (not append-only one-liners; mixed with status) |
| index.md | Missing. bu-identity/README.md is a local index only |
| Lint | Missing (no check for orphans, stale numbers, contradictions between notes, backlog vs log) |
| Query-to-page loop | Informal (decisions land in session log, not always in topic notes) |
| Strengths beyond pattern | lessons.md, backlog table, Claim/Decision lines, semantic layer with check script |

## 4. Proposed layout
Option A (moves nothing, adds two files): add `notebooks/knowledge/index.md` (one line per note: path, type, one-sentence summary, last-verified date; grouped: Decisions/experiments, Specs, Lessons, Backlog, Session logs, BU identity, Semantic layer pointer) and `notebooks/knowledge/log.md` (append-only, `## [YYYY-MM-DD] ingest|query|lint|decision | title`, one line + links). Session logs stay as the narrative/status; log.md is the greppable spine. Add minimal frontmatter (`type`, `updated`, `status`) to topic notes only when touched.

Option B (small moves, later): `sessions/` <- session-log-*.md; `topics/` <- canonical-prompt-experiment, prompt-v3-results, bu-prompt-spec, bu-framework-survey, deterministic-cdt-plan, brand-signal-experiments; keep backlog.md, lessons.md, index.md, log.md at top; bu-identity/ unchanged. Cost: broken links in CLAUDE.md, backlog.md, handoff skill, hooks (SessionStart reads session-log path). Recommend A first.

Raw layer: do not copy data in; list in index.md as read-only pointers (semantic/, data/work/, BQ tables, source docs) and add a CLAUDE.md rule not to edit them as notes.

## 5. Operations as Claude Code pieces
- CLAUDE.md rule (short): index.md + log.md must be updated in the same commit as any knowledge note; note frontmatter fields; contradictions are flagged, not overwritten; raw/pointer areas are read-only; numbers in notes cite file/command (matches the Claim: rule).
- Skill `wiki-ingest` (LLM): take a new source/result (experiment output, user decision, paper), write/extend a topic note, update index, append log, list notes touched. Extends the existing /handoff skill rather than replacing it.
- Skill `wiki-query` (LLM): read index first, answer with links, offer to file the answer.
- Skill `wiki-lint` (LLM + script): LLM part = contradictions and stale claims between notes; script part (below).
- Plain script (no LLM), run by a hook or command: check every file is in index.md, relative links resolve, frontmatter present, backlog IDs referenced exist, log.md entries well-formed, `Status` line date in newest session log. Could live in the repo (uv run) beside check_semantic.py.
- Hook: SessionStart already prints Status/Open; add "index.md last updated / lint warnings count". Optional PostToolUse/Stop hook (command type, no LLM) that warns when a knowledge note changed but index.md/log.md did not.
- Claude Code mod (in-process plugin, no LLM calls): status-line item "wiki: N notes, M lint warnings, log last entry date"; a pane listing index.md entries with staleness; slash commands `/wiki-lint-quick` that runs the script and shows results. Authoring details: see the plugin-authoring skill (not read in this job; unverified feasibility of each surface).
- Permissions: deny Edit on semantic/metadata and generated files; index.md/log.md editable by the LLM only via the skills.

## 6. Risks
- Model collapse / flattening: topic notes carry measured numbers; repeated rewriting could drift them. Mitigate: append-only log, numbers keep source file + command, edit in place only with a log line, git diff review by the user.
- Duplicate truth: session log, backlog, topic note and lessons already overlap; a wiki adds a fifth place. Mitigate: index is a catalogue only, no new summaries.
- User reviews by hand (memory): more LLM-written pages = more review load. Keep ingest small and confirm page lists.
- Cost: ingest touching 10-15 pages is heavy; here notes are few (~12), so keep it to 1-3 pages.
- Not a RAG replacement need: at this size index.md suffices; qmd/vector search is unnecessary.
- Misleading confidence in synthesized pages; require status (decided / measured / hypothesis).

## 7. Open questions for the user
1. Option A (index.md + log.md only) now, or A then B (move into sessions/ and topics/)?
2. Should log.md replace the "Done" sections of session logs (one spine), or stay a thin index beside them?
3. Do you want the lint script + status-line mod (no LLM cost), or only skills and a CLAUDE.md rule for now?
