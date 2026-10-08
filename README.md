# codex-harness

Claude (or you) orchestrates, **Codex is the worker**, **a human reviews every round**. Works in any git project.
Stdlib Python only. Command: `harness` (symlink in `~/.local/bin`).

```
 plan (task.md + check) ─▶ run ─▶ Codex works (sandbox, HANDOFF.md) ─▶ acceptance check ─▶ REVIEW (you)
        ▲                                                                                     │
        └──── harness feedback <job> "…"  (same Codex session: codex exec resume) ◀───────────┤
                                                                       harness accept <job> ◀─┘ (commit outside)
```

## Commands (run inside the project)

| Command | What it does |
|---|---|
| `harness init` | create `.harness/`; append the "Lessons and multi-model work" section to CLAUDE.md (if present) and AGENTS.md (created if missing), never overwriting |
| `harness new <job> --task task.md --check-cmd 'CMD' --scope PATH...` | create a job (`--check FILE`, `--model`, `--effort`, `--max-rounds`, `--lessons FILE`) |
| `harness run <job> [--bg]` | round 1: `codex exec` in a workspace-write sandbox |
| `harness feedback <job> "text"` / `-f file` `[--bg]` | next round in the SAME session with your feedback |
| `harness review <job>` | review packet of the last round |
| `harness accept <job>` / `harness reject <job> "why"` | close the job (the harness never commits) |
| `harness data <job>` | list the worker's data requests with a static SQL check (OK / FLAG / REJECT) |
| `harness data <job> --done FILE... [--note T] [--bg]` | deliver pulled data (copied to `jobs/<job>/data/`), resume the same session (counts as a round) |
| `harness lessons <job>` | retrospective draft: what went wrong per round + the worker's `Lessons (draft)` → `retro.md` |
| `harness status` | per job: status, round, minutes, check, HANDOFF Status line (+ its age) and the last activity in `codex.log` |
| `harness monitor [sec]` | the same table, refreshed live + macOS notification when a job needs you |

Defaults: model `gpt-6.1-sol`, reasoning `medium` (user decision 2026-10-08; `--effort high` for hard design work),
max 5 rounds (env `HARNESS_MODEL`, `HARNESS_EFFORT`).

Before `new`: the **scope comes from the user** (the orchestrator asks which paths the worker may write and how big
the round may get), and worker questions (`needs_input`) go to the user verbatim; the orchestrator / operator
never answers them on the user's behalf.

## What the worker must do (injected into every first prompt)

- Write only inside `--scope` paths and its job folder; never commit; no network (sandbox).
- Keep `.harness/jobs/<job>/HANDOFF.md` current from the first minute (Status / Done / Next / Files / Decisions /
  Open issues / How to verify), so any model can take over if the run dies or tokens run out.
- `## Status` is one line, **rewritten in place** on every update (never appended below); Done / Decisions /
  Open issues may grow. Feedback rounds repeat this reminder.
- It cannot ask mid-run: it records assumptions and ends with `status: needs_input` + `questions`.
- Mistakes go into HANDOFF.md under `## Lessons (draft)` (Problem / Cause / Fix / Prevent).
- No network, never BigQuery: missing data → `status: needs_input` + exact read-only SQL in `data_requests`.
- Final message = JSON (`--output-schema`): status, summary, files, questions, next, data_requests.
- The first prompt also carries a compact LESSONS block: title + Prevent line of every `[who: codex]` /
  `[who: both]` entry in `LESSONS.md` (next to harness.py; env `HARNESS_LESSONS`) and in the project lessons file
  (`--lessons`, default the first of `notebooks/knowledge/lessons.md`, `docs/lessons.md`; skipped if missing).

## Data requests (Codex has no network)

1. Worker ends with `needs_input` and `data_requests` (purpose, sql, tables, expected_rows). review.md shows
   `DATA REQUESTED (n)`; status shows `needs_input +ndata`.
2. Operator: `harness data <job>` → static check per SQL: one SELECT/WITH statement = OK; INSERT / UPDATE / DELETE /
   MERGE / CREATE / DROP / ALTER / TRUNCATE or several statements = REJECT; other oddities = FLAG.
3. Orchestrator shows the SQL to the user; after approval: dry run (bytes), read-only pull to parquet/csv.
   The operator never runs BigQuery.
4. `harness data <job> --done path.parquet ... --note "..."` → files copied to `.harness/jobs/<job>/data/`, the
   worker resumes in the same session with the file list (rows / columns).

## Retrospective (every job, accepted or rejected)

`harness lessons <job>` drafts the facts (check failures, needs_input, errors, data rounds, rounds used) and the
worker's `Lessons (draft)`. The operator turns them into entries (Problem / Cause (verified) / Fix / Prevent / Seen,
`[who]` `[area]`): workflow → `LESSONS.md`, domain → the project lessons file. The orchestrator approves and commits.

## Command records (everything that ran, with its output)

- `.harness/commands.log`: every `harness ...` invocation appends one JSON line: `ts`, full `argv`, `cwd`, `actor`
  (env `HARNESS_ACTOR` = user | orchestrator | operator, default `unknown`), `job`, `exit_code`, `duration_s`, and the
  full `stdout` / `stderr` (teed, so you still see it; `monitor` keeps only the last 20k chars). Internal
  `_worker` runs are logged too. Logging errors never fail the command. Read: `tail -1 .harness/commands.log | python3 -m json.tool`.
- `rounds/<n>/command.json`: the exact `codex exec` / `codex exec resume` argv, cwd, model, effort, sandbox,
  session_id, `codex --version`, sha256 of prompt.md and check.sh, started / ended, exit_code, duration_s.
  Codex output itself is in `codex.log`.
- `rounds/<n>/check_command.json`: argv (`bash check.sh`), the check.sh content at that time + sha256,
  exit_code, stdout, stderr, timing (check.txt stays).
- review.md has a short `## Commands` section: codex argv + exit, check argv + exit, path to commands.log.

## Status / monitor columns

`MIN` = minutes since the round started (running) or the last round's duration (stopped). The HANDOFF column is
the worker's `## Status` line with the file's age in minutes, so a stale HANDOFF is visible. The `└ log:` line is
the last event in the current round's `codex.log` (`says:` agent message, `runs:` command, `edits:` file,
`thinking:`, `finished:` tokens line), trimmed to one line, so you see activity even when HANDOFF lags.

## Files

```
<project>/.harness/                 (added to .git/info/exclude)
  result_schema.json
  jobs/<job>/task.md  check.sh  state.json  HANDOFF.md
  commands.log                      one JSON line per `harness` call: ts, argv, cwd, actor, job, exit_code, duration_s, stdout, stderr
  jobs/<job>/rounds/<n>/prompt.md  codex.log  result.json  check.txt  review.md
  jobs/<job>/rounds/<n>/command.json  check_command.json
  jobs/<job>/data/  (pulled data)   jobs/<job>/retro.md  (retrospective draft)
  OPERATOR_HANDOFF.md  (the operator agent's own handoff)
```

Statuses: created → running → awaiting_review | needs_input | blocked | failed | error → (feedback) running … →
accepted | rejected. A dead background worker shows as `error`.

## Taking over a job with another model

Read `state.json` (session id, round) and `HANDOFF.md` (Next). To continue in Codex: `harness feedback <job> "…"`.
To continue elsewhere: give the other model `task.md` + `HANDOFF.md` + the last `review.md`.

## Tested

2026-10-08: full loop with a stub Codex (fail → feedback → pass → accept) and with real `gpt-6.1-sol`
(round 1 check FAIL, feedback, round 2 in the same session id, check PASS).
2026-10-08: HANDOFF Status rewrite rule + log activity / elapsed minutes in status and monitor, tested with a
stub Codex (log formats: agent message, exec, diff, unknown; running and stopped jobs).
2026-10-08: lessons injection, `harness lessons`, `harness data` (+ SQL check), init sections: stub-tested
(needs_input with 3 data requests → data --done → done; init twice is idempotent).
2026-10-08: commands.log / command.json / check_command.json / review Commands section: stub-tested (logged
exit codes 0, 1 and 2, actor from env, output still shown, logging failure does not fail the command).
