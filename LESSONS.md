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
- Prevent: set the effort explicitly (user default since 2026-10-08: medium); check the log header line before trusting a run.
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

## L11. Backticks in an unquoted heredoc ran as commands   [who: claude] [area: process]
- Problem: text written through `python3 - <<EOF` lost its backticked paths; the shell tried to run them
  ("Permission denied", "No such file or directory").
- Cause: an unquoted heredoc delimiter lets the shell do command substitution on backticks.
- Fix: repaired the two files by hand edit.
- Prevent: quote the delimiter (`<<'EOF'`) whenever the body contains backticks or `$`; read the shell's stderr
  even when the script prints "ok".
- Seen: 2026-10-08, handoff rule edit.

## L12. git blocked by the Xcode license (no sudo)   [who: both] [area: git]
- Problem: every git command failed: "You have not agreed to the Xcode license agreements"; the user has no sudo.
- Cause: /usr/bin/git is a shim that uses the selected developer dir (Xcode.app), whose license was reset (likely an
  Xcode update).
- Fix: `export DEVELOPER_DIR=/Library/Developer/CommandLineTools` (Command Line Tools git, no license prompt).
- Prevent: if git fails with the Xcode license message, use DEVELOPER_DIR=/Library/Developer/CommandLineTools;
  never ask for sudo first.
- Seen: 2026-10-08.

## L13. A round with no size limit ran 37 min and produced 21 files   [who: both] [area: process]
- Problem: cdt-drift-analysis round 1 took 37 min, wrote 21 files (drift_examples.csv 13.8 MB / 54,656 rows, report.md
  89 KB / 914 lines) for 3 requested deliverables, with no short summary.
- Cause: task.md set no limits on time, number of files or output size (verified: state.json, result.json, task.md).
- Fix: round 2 feedback set 25 min, no new files, CSV under 5,000 rows, a 40-line summary.
- Prevent: every task.md states max minutes, allowed files, max output size, "no extra analyses"; the user sets the scope.
- Seen: 2026-10-08, cdt-drift-analysis.

## L14. Codex sandbox constraints   [who: codex] [area: codex-cli]
- Problem: (a) uv needed a cache inside the writable paths; (b) a broad `rm -f` cleanup was rejected by the execution
  guard (codex.log line 97494 "exec_command failed ... Rejected").
- Cause: workspace-write sandbox allows writes only in the project / scope paths and blocks risky commands. (a) is
  worker-reported (the original failure line was not found; every later call uses a local UV_CACHE_DIR).
- Fix: `UV_CACHE_DIR=<scope>/.uv-cache uv run --offline --no-sync ...`; delete only an explicit whitelist of files.
- Prevent: task.md for uv projects gives the UV_CACHE_DIR / --offline line; workers never use broad rm.
- Seen: 2026-10-08, cdt-drift-analysis.

## L15. Reproducible scripts must not write harness state   [who: codex] [area: harness]
- Problem: analysis.py rewrote HANDOFF.md with an "in progress" Status every time it was rerun (incl. by the check).
- Cause: the script mixed analysis output with job bookkeeping (worker-reported; the final analysis.py no longer
  writes HANDOFF and the check rerun left it "Done").
- Fix: removed the HANDOFF write from analysis.py.
- Prevent: scripts write only their own outputs; HANDOFF.md / state.json are written by the worker or the harness.
- Seen: 2026-10-08, cdt-drift-analysis.
