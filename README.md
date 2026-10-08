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
| `harness new <job> --task task.md --check-cmd 'CMD' --scope PATH...` | create a job (`--check FILE`, `--model`, `--effort`, `--max-rounds`) |
| `harness run <job> [--bg]` | round 1: `codex exec` in a workspace-write sandbox |
| `harness feedback <job> "text"` / `-f file` `[--bg]` | next round in the SAME session with your feedback |
| `harness review <job>` | review packet of the last round |
| `harness accept <job>` / `harness reject <job> "why"` | close the job (the harness never commits) |
| `harness status` | one line per job |
| `harness monitor [sec]` | live table + macOS notification when a job needs you |

Defaults: model `gpt-6.1-sol`, reasoning `high`, max 5 rounds (env `HARNESS_MODEL`, `HARNESS_EFFORT`).

## What the worker must do (injected into every first prompt)

- Write only inside `--scope` paths and its job folder; never commit; no network (sandbox).
- Keep `.harness/jobs/<job>/HANDOFF.md` current from the first minute (Status / Done / Next / Files / Decisions /
  Open issues / How to verify), so any model can take over if the run dies or tokens run out.
- It cannot ask mid-run: it records assumptions and ends with `status: needs_input` + `questions`.
- Final message = JSON (`--output-schema`): status, summary, files, questions, next.

## Files

```
<project>/.harness/                 (added to .git/info/exclude)
  result_schema.json
  jobs/<job>/task.md  check.sh  state.json  HANDOFF.md
  jobs/<job>/rounds/<n>/prompt.md  codex.log  result.json  check.txt  review.md
```

Statuses: created → running → awaiting_review | needs_input | blocked | failed | error → (feedback) running … →
accepted | rejected. A dead background worker shows as `error`.

## Taking over a job with another model

Read `state.json` (session id, round) and `HANDOFF.md` (Next). To continue in Codex: `harness feedback <job> "…"`.
To continue elsewhere: give the other model `task.md` + `HANDOFF.md` + the last `review.md`.

## Tested

2026-10-08: full loop with a stub Codex (fail → feedback → pass → accept) and with real `gpt-6.1-sol`
(round 1 check FAIL, feedback, round 2 in the same session id, check PASS).
