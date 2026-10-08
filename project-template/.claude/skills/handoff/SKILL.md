---
name: handoff
description: Use before /clear, before ending a session, or when the user says "handoff", "ทำ handoff", "เตรียม clear", "ส่งต่อ session". Writes the session log so the next session (any model) can continue, then commits it.
---

# Handoff before /clear

The SessionStart hook prints the session log Status / Open sections into the next session, and the SessionEnd
hook only writes a raw snapshot (`.claude/handoff-auto/`) when this skill was skipped. The content that matters
comes from here. Paths come from `.claude/handoff.json` (`sessionLog` glob, `wikiDir`, `lessons`); clear-guard
reads the same file.

## Steps

1. Find the session log: newest file matching `sessionLog`. If today has none, create one with `*` replaced by
   today's date (`YYYY-MM-DD`) that continues the previous one (first line points to it), with sections
   `## Status`, `## Done`, `## Decisions`, `## Open`. If `wikiDir` has an `index.md`, add the new log there (/wiki).
2. Rewrite `## Status` **in place** (do not append): one short paragraph with date and time, branch, what is
   running, what waits for whom, and the exact next step. Include known gotchas the next session needs.
3. Update `## Done` (paths, commits), `## Decisions` (`Decision:` lines the user took this session) and
   `## Open` (decisions still waiting for the user, numbered; `Proposal:` lines with a recommendation).
4. If a Codex job ran or is running: make sure `.harness/OPERATOR_HANDOFF.md` `## Status` matches
   `harness status`; fix it if stale.
5. Lessons: if something went wrong this session and has no lesson yet, draft it (the project lessons file or the
   harness LESSONS.md, both listed in `lessons`) and list it under Open for the user to approve.
6. Commit the session log and any other docs this session finished (not data, not unrelated work in progress).
   On macOS, if git fails with the Xcode license message: `export DEVELOPER_DIR=/Library/Developer/CommandLineTools`
   (harness lesson L12). Message: `docs: session log handoff <date>`.
7. Reply with: the new Status line, the Open list, the commit hash, and "พร้อม /clear". List anything left
   uncommitted on purpose.

## Rules

- Facts only from this session's evidence; mark guesses `Status: hypothesis`.
- Never copy the raw transcript into the log; a pointer to its path is enough.
- Keep the Status short: the SessionStart hook prints at most 20 lines of it and 30 lines of Open.
