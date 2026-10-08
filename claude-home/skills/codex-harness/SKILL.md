---
name: codex-harness
description: Use when the user wants Codex to do work as a worker under Claude's orchestration, or says "ส่ง codex ไปทำ" / "ให้ codex ทำ" / "use codex as worker". Main session orchestrates only; an Opus "harness operator" agent runs the codex-harness loop; the user reviews every round; every job ends with a lessons entry.
---

# Codex as worker (codex-harness)

Roles (user decisions 2026-10-08):
- **User**: reviews and decides every round.
- **Main session (orchestrator)**: writes the job plan with the user, relays short reports and the user's decisions,
  commits. Never reads codex.log or long outputs (protect context).
- **Harness operator** (Agent, model opus, background): creates / runs / waits for jobs with the `harness` CLI,
  verifies results, writes `.harness/jobs/<job>/orchestrator_review.md`, applies the user's decisions
  (`harness feedback|accept|reject`) only when the orchestrator relays them, returns <20-line summaries.
- **Codex** (gpt-6.1-sol, reasoning medium): the worker, in a sandbox; keeps HANDOFF.md; never commits.

Tool: `harness` (~/tools/codex-harness, README there). No automatic retries; no approval on the user's behalf.

## Loop

1. **Lessons first.** Operator and worker read `~/tools/codex-harness/LESSONS.md` and the project's lessons file
   (e.g. `notebooks/knowledge/lessons.md`) before the job; task.md cites the entries that apply.
2. **Plan** (orchestrator + user): ASK THE USER FIRST what they want (scope, outputs, size limits); then task.md (goal, inputs, output paths, project rules, what not to touch) and an
   acceptance check that exits 0 only when the work is right.
3. **Operate** (operator): `harness new ... && harness run <job> --bg`; user can watch with `harness monitor`.
4. **Review** (operator -> orchestrator -> user): verified summary, problems, worker questions, recommendation.
   The user decides: feedback / accept / reject. The orchestrator relays it to the operator.
5. **Close**: after accept, the orchestrator runs the project tests and commits (worker and operator never commit).
6. **Retrospective (mandatory)**: the operator drafts lessons from the job — anything that went wrong or cost a
   round, for Claude or Codex — as entries `Problem / Cause / Fix / Prevent / Seen` in LESSONS.md (workflow) or the
   project lessons file (domain). The orchestrator reviews and commits them. Lessons that become a rule should
   also be enforced where possible (harness worker rules, checks, skill text).

## Rules

- Handoff files: operator `.harness/OPERATOR_HANDOFF.md`, worker `.harness/jobs/<job>/HANDOFF.md`, orchestrator the
  session log `## Status`. Name the handoff path in every agent prompt; ask for it in every report.
- Paid / outward actions (BigQuery, embeddings, deploys) are forbidden for workers unless the user approved them for
  that job; data is pulled by the orchestrator (read-only, query shown first) and given to Codex as files.
- The worker cannot ask mid-run; it ends with `needs_input` + questions. Report the questions to the user verbatim;
  the user answers; relay the answer. Never answer for the user.
- If a job dies or tokens run out: `state.json` + `HANDOFF.md` let any model continue (`harness feedback`).
- Propose new persistent artifacts (skills, global config) to the user before creating them (LESSONS L10).
- Agents and workers state causes / conclusions as `Claim: ... | Status: hypothesis|verified | Evidence: ...`
  lines (global rule in ~/.claude/CLAUDE.md and ~/.codex/AGENTS.md); ask for them in every prompt.
