<!-- agent-kit:project-rules (from ~/agent-kit/project-template; edit freely, the installer only adds this once) -->
## Lessons and multi-model work (Claude + Codex)

- **Read lessons before starting work**: the files listed under `lessons` in `.claude/handoff.json` (this project's
  lessons and `~/tools/codex-harness/LESSONS.md`). Apply the `Prevent` lines.
- **Write a lesson when something goes wrong** (failed check, wrong claim, silent data loss, wasted round):
  `## P<n>. title [who: claude|codex|both] [area: ...]` + Problem / Cause (verified) / Fix / Prevent / Seen.
  Project lessons go to the project file, workflow lessons to the harness LESSONS.md.
- **Handoff, always**: the session log (`sessionLog` in `.claude/handoff.json`) keeps `## Status` rewritten in
  place plus Done / Decisions / Open. Run `/handoff` before `/clear`; clear-guard asks when the log is stale.

## Knowledge wiki (`wikiDir` in `.claude/handoff.json`)

- **Read `index.md` there first** for project knowledge; follow its links instead of searching. Pages marked
  `superseded` are history: use `superseded_by`.
- **Every note change updates the wiki in the same commit** (skill `/wiki`): new page → index line; status change →
  frontmatter + index line; knowledge event → one entry at the end of `log.md`. `log.md` is append-only.
- Frontmatter on every page: `type`, `status` (active | reference | done | superseded), `updated`, `sources`.
  Check with `python3 ~/.claude/skills/wiki/wiki_lint.py` (Codex: `~/.codex/skills/wiki/`).
