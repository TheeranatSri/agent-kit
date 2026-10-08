# Lessons (Claude + Codex workflow)

Shared memory of mistakes, so Claude (orchestrator / operator) and Codex (worker) do not repeat them.
Read before starting a job; add an entry after every job (accepted or rejected) and whenever something goes wrong.
Project-specific (domain) lessons live in the project, e.g. npd-comparables/notebooks/knowledge/lessons.md.

Entry format (keep each under ~8 lines):

```
## L<n>. <short title>   [who: claude | codex | both] [area: harness | codex-cli | git | data | review | process]
- Problem: what went wrong (observable symptom).
- Cause: why it happened (verified, not guessed).
- Fix: what was done.
- Prevent: the rule / check that stops it next time (and where it is enforced, if anywhere).
- Seen: date, job / commit.
```

## L1. Codex ran with reasoning effort "none"   [who: codex] [area: codex-cli]
- Problem: first 8 Codex runs started with `reasoning effort: none`; too weak for design work.
- Cause: `codex exec` default; the model name alone does not set effort.
- Fix: stopped and restarted with `-c model_reasoning_effort="high"`.
- Prevent: harness default effort = high; check the log header line before trusting a run.
- Seen: 2026-10-08, prompt v3 per BU.

## L2. HANDOFF Status went stale   [who: codex] [area: harness]
- Problem: monitor showed "analysis not started" while the worker was well into the analysis.
- Cause: the worker appended progress at the end of HANDOFF.md instead of rewriting the `## Status` line.
- Fix: worker rules say Status is rewritten in place; monitor also shows the last log line.
- Prevent: harness rules (WORKER_RULES) + monitor log column.
- Seen: 2026-10-08, job cdt-drift-analysis.

## L3. `codex exec resume` rejects -s / -C / --color   [who: claude] [area: codex-cli]
- Problem: resume command built like the first run would fail.
- Cause: resume supports fewer flags than exec.
- Fix: pass sandbox as `-c sandbox_mode="workspace-write"`, run with cwd = project root, drop --color.
- Prevent: check `codex exec resume --help` after a Codex CLI upgrade; smoke test with a real resume.
- Seen: 2026-10-08, harness build.

## L4. macOS bash has no associative arrays   [who: claude] [area: process]
- Problem: `declare -A` failed, leaving a stray folder `0/`.
- Cause: /bin/bash on macOS is 3.2.
- Fix: generate files with Python instead.
- Prevent: use Python (or plain loops) for maps in shell scripts on macOS; check for stray outputs after a failed command.
- Seen: 2026-10-08.

## L5. Codex cannot ask questions mid-run   [who: both] [area: harness]
- Problem: no way for a worker to wait for the user.
- Cause: `codex exec` is non-interactive (approval: never).
- Fix: worker records the assumption and ends with `status: needs_input` + questions; the orchestrator brings them to the user.
- Prevent: output schema + worker rules.
- Seen: 2026-10-08.

## L6. A failing test was hidden by a pipe   [who: claude] [area: git]
- Problem: committed with a failing test.
- Cause: `pytest | tail` returns tail's exit code, not pytest's.
- Fix: check `${PIPESTATUS[0]}` / run without the pipe before committing.
- Prevent: always read the real exit code before a commit.
- Seen: 2026-10-06.

## L7. Wrong cause stated as fact   [who: claude] [area: review]
- Problem: told the user the 0847 miss came from USP length; a test refuted it (real cause: identity text / CDT label).
- Cause: explained before testing.
- Fix: corrected the slide and the log.
- Prevent: say "hypothesis" until a test confirms; run the test first when it is cheap.
- Seen: 2026-10-06.

## L8. Multi-value spans failed a naive check   [who: claude] [area: review]
- Problem: span check reported 18 "NOT FOUND" that were real.
- Cause: agents packed several spans in one cell with " | "; the check looked for the whole cell.
- Fix: split on " | " and check each piece against all source texts.
- Prevent: define the span format in the spec (one span per row, or " | " separated) and check accordingly.
- Seen: 2026-10-07, part breakdown.

## L9. Main-session context filled with worker logs   [who: claude] [area: process]
- Problem: the orchestrator read long Codex logs and agent reports, using context fast.
- Cause: orchestrator doing operator work.
- Fix: a separate Opus "harness operator" agent runs jobs and returns <20-line summaries with file paths.
- Prevent: never read codex.log in the main session; ask the operator.
- Seen: 2026-10-08.

## L10. Built something the user did not ask for   [who: claude] [area: process]
- Problem: created the codex-harness skill without asking.
- Cause: assumed it was wanted.
- Fix: told the user, asked whether to keep / update / remove.
- Prevent: propose new persistent artifacts (skills, global config) before creating them.
- Seen: 2026-10-08.
