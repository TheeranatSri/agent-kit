# Global instructions (all projects)

## Learn from mistakes (Claude + Codex)

- Before starting work, read the lessons files and apply their `Prevent` lines:
  `~/tools/codex-harness/LESSONS.md` (workflow: Claude, Codex, harness, git) and the project's own lessons file
  (convention: `notebooks/knowledge/lessons.md` or `docs/lessons.md`; create it when the first lesson appears).
- When something goes wrong (failed check, wrong claim, silent data loss, wasted round), add an entry:
  `## L<n>. title [who: claude|codex|both] [area: ...]` + Problem / Cause (verified, not guessed) / Fix / Prevent /
  Seen. Workflow lessons go to the harness LESSONS.md, project lessons to the project file. A lesson that becomes a
  rule should be enforced where possible (test, check, CLAUDE.md / AGENTS.md).
- Every project's CLAUDE.md and AGENTS.md (when they are created or edited) should carry a short "Lessons and
  multi-model work" section pointing to these files, so Claude and Codex follow the same rules.

## Claude + Codex roles

- The user reviews and decides every round. The main Claude session orchestrates, relays short reports and the
  user's decisions, and commits. An Opus operator agent runs Codex jobs with the `harness` CLI
  (`~/tools/codex-harness`, skill `codex-harness`). Codex (gpt-6.1-sol, reasoning MEDIUM) is the worker in a sandbox,
  keeps HANDOFF.md current, never commits. Every job ends with a retrospective (new lessons).

## Handoff

- **Handoff, always** (so any model can continue if one stops or runs out of tokens): the main session keeps
  the project's session log (e.g. `notebooks/knowledge/session-log-<date>.md`) with a `## Status` line rewritten
  in place plus Done / Decisions / Open; the harness operator keeps `.harness/OPERATOR_HANDOFF.md`; every Codex job keeps `.harness/jobs/<job>/
  HANDOFF.md`; every background Claude agent with a multi-step task keeps a handoff file named in its prompt.
  Sections: Status (one current line) / Done (paths) / Next (exact steps) / Decisions & open questions / How to verify.
- Before creating a Codex job, ask the user what they want (scope, outputs, limits); write task.md from that.
- Codex questions (`needs_input`) go to the user verbatim; the user answers. Never answer them on the user's behalf.
- Codex usage / cost: the user tracks it; no cost gates for Codex.

## Claims (all projects; makes reasoning auditable without logging thinking)

- Whenever you state a cause, a conclusion, or why something happened / will work, write it as one line in the
  visible reply: `Claim: <statement> | Status: hypothesis|verified | Evidence: <file, command, test, number>`.
- `verified` only with concrete evidence (a file path, a command and its result, a test, a count). Otherwise it is
  `hypothesis`, and say what test would confirm it. Never present a hypothesis as fact (lesson L7).
- When a later test confirms or refutes a claim, write a new Claim line with the result; a refuted claim becomes a
  lesson. The IO-log hook extracts `Claim:` lines into the log, so no extra LLM cost.

## Structured lines (all projects; parsed by the IO-log hook, no LLM cost)

Write these as single lines in the visible reply (Codex: final message / HANDOFF.md) when they apply:

- `Claim: <statement> | Status: hypothesis|verified | Evidence: ...` (see Claims above)
- `Proposal: <id> | Options: A) ... B) ... | Recommend: A | Rationale: ...`
- `Decision: <id> | Choice: B | By: user | Note: ...` (record the user's choice; match the Proposal id)
- `Question: <id> | To: user | From: <actor> | ...` (open questions, incl. Codex questions relayed verbatim)
- `Assumption: ... | Rationale: ... | Risk: ... | Revisit: ...` (anything chosen without the user's answer)
- `Failure: want ... | actual ... | evidence ... | cause ... | Status: hypothesis|verified`
- `Done: ... | Verified: <test / command / count> | Commit: <hash>`
- `Check: <step> | <item> | Criterion: ... | Actual: ... | Evidence: ... | Pass: yes|no` for data analysis; several
  Check lines per step. Steps and what to check:
  - `source`: data source / version, column types, units, missing, odd values, duplicate keys
  - `scope`: population, period, filters, exclusions, what one row represents
  - `transform`: rows before -> after, why they changed, whether joins duplicate or drop rows, totals still reconcile
  - `method`: formula, denominator, weights, missing / outlier handling, assumptions of the method
  - `result`: numbers re-checked another way, tables and charts agree, how strongly the evidence supports the conclusion
