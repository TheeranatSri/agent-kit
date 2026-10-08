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
- Seen: 2026-10-06. Again 2026-10-08 (knowledge-index): Codex reported log.md as 135 lines without counting; actual 124.

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

## L16. Codex plugin hooks fail with `node: command not found`   [who: claude] [area: claude-code env]
- Problem: SessionStart:clear hook error `/bin/sh: node: command not found` (Codex plugin hooks run `node ...`).
- Cause (verified): node comes only from nvm, loaded in `~/.bash_profile`; the Claude Code process PATH has `~/.local/bin` but no nvm dir, and hooks run via `/bin/sh` with that PATH.
- Fix: `ln -s ~/.nvm/versions/node/v24.21.0/bin/node ~/.local/bin/node`; hook script exits 0 under a minimal PATH.
- Prevent: the link pins v24.21.0; after `nvm install`/removing that version, re-point the link. Any tool a hook needs must be on the Claude process PATH, not only in shell rc files.
- Seen: 2026-10-08, after /clear.

## L17. Acceptance check passes when git fails, and only works before commit   [who: claude] [area: harness check]
- Problem: knowledge-index check.py compared note bodies with `git show HEAD:<file>`; if git failed it got an empty
  string and skipped the body / scope checks (pass). After the orchestrator committed the job, the same check
  reported FAIL because HEAD now had the frontmatter.
- Cause (verified): the check used `HEAD` as the baseline and treated empty git output as "nothing to compare".
- Fix: re-verified against the pre-job commit (`5542896~1`): 0 of 19 bodies changed.
- Prevent: checks that call git must fail on a non-zero git exit; pin the baseline commit when the job is created
  (e.g. `BASE=$(git rev-parse HEAD)` written into the check) instead of `HEAD`.
- Seen: 2026-10-08, knowledge-index (npd-comparables).

## L18. Abbreviated SQL shown to the user was run and failed   [who: claude] [area: review / BigQuery]
- Problem: the user pasted the SQL from the chat into the BigQuery console and got `Syntax error: Unexpected "." at [4:83]`.
- Cause (verified): the main session shortened the SQL in its reply (`... 8]` inside UNNEST, `vw_rows AS (...)`);
  the file itself had passed a dry run.
- Fix: showed the full file content (comments stripped).
- Prevent: in chat show a SHORT sketch (user preference 2026-10-08) but label it as not runnable
  (`-- sketch, not runnable; full SQL: <path>`) and give the file path; the user reads / runs the file itself.
  Never present a shortened query as if it could be pasted.
- Seen: 2026-10-08, cdt_annotations_products.sql.

## L19. Generic hook picked the session log by mtime, the project hook by name   [who: claude] [area: process / hooks]
- Problem: the agent-kit template hooks (and clear-guard 0.2.0, wiki-note) chose the "newest" session log by
  mtime; npd's own hooks chose the last file by name. When an older log was edited later (a Codex job touched
  `session-log-2026-10-06.md`), the template printed the wrong Status / Open.
- Cause (verified): `ls -t` / sort by `mtimeMs` in the generic code; found by diffing old vs new hook output on a
  clone of npd before switching (old picked 10-08, new picked 10-06).
- Fix: last file in name order (dated names) in handoff_config.sh, clear-guard and wiki-note; tests for an older log
  with a newer mtime.
- Prevent: when a generic version replaces a working project script, run both on a clone of the real project
  (same inputs, edge cases such as stale / fresh) and diff the outputs before switching.
- Seen: 2026-10-08, npd-comparables move to the agent-kit template.

## L20. `codex exec --search` is not an exec option   [who: claude] [area: codex-cli]
- Problem: two research runs exited 2 at once (`unexpected argument '--search'`); a round of waiting lost.
- Cause (verified): `--search` belongs to the top-level `codex` command (`codex --search exec ...`); I read only a
  grep of `codex exec --help`, where the word appeared in another option's text.
- Fix: `codex --search exec --skip-git-repo-check -s read-only -m ... -o out.md -`.
- Prevent: before a background Codex run, smoke-test the exact argv in the foreground with a trivial prompt (or
  `--help` of the exact subcommand, read in full); harness jobs have no network, so web research uses this form.
- Seen: 2026-10-08, context-tools / mods research.

## L21. Worker sandbox cannot bind localhost, so HTTP acceptance tests stop inside it   [who: both] [area: harness / codex-cli]
- Problem: Rounds 2 and 3 ended with worker status `blocked`, but the same check.sh exited 0 when the operator ran it outside the sandbox. Each round needed an operator rerun to learn that the work was correct.
- Cause (verified): the workspace-write sandbox rejects `socket.bind(('127.0.0.1', 0))` with PermissionError errno 1. Worker HANDOFF rounds 1-3 point to tests/test_pipeline_r1.py:160. The operator's check.sh runs printed `ok server /overview ...` and exited 0.
- Fix: The operator reran check.sh outside the sandbox after every round, and the worker kept its own extra tests free of sockets.
- Prevent: In task.md, mark any acceptance step that needs localhost as "operator-run". The harness should run the check itself after the round, outside the sandbox (it already does), and the operator treats that result as authoritative. Workers should report "blocked by sandbox socket" as `done` + Open issue, not `blocked`, when every other check passes.
- Seen: 2026-10-08, pipeline-r1 rounds 1-3.

## L22. The operator agent ran in an isolated git worktree, not the main checkout   [who: claude] [area: process / harness] (orchestrator)
- Problem: The job, .harness/ and the worker's changes lived in .claude/worktrees/agent-<id>. The orchestrator had to copy the files to main, fast-forward the worktree before round 2 (stash / ff / pop), and copy them back again after accept.
- Cause (verified): the orchestrator (Claude) launched the operator Agent with `isolation: "worktree"`. Its sandbox refused git in the shared checkout ("must target its own worktree"). Also, `git status` in the worktree shows `?? .harness/`, so `harness init`'s exclude entry did not take effect there.
- Fix: The job ran in the worktree, the orchestrator synced by hand, and the operator reported the location in every report.
- Prevent: Launch the harness operator WITHOUT worktree isolation (it must run in the project checkout it reports on). If isolation is required, name the worktree path in task.md and the review, and plan the sync step. Also, `harness init` could write the exclude entry to the common git dir (`git rev-parse --git-common-dir`/info/exclude) so worktrees also hide .harness/.
- Seen: 2026-10-08, pipeline-r1.

## L23. The agent sandbox refused `--check-cmd 'bash …'`   [who: claude] [area: harness]
- Problem: `harness new ... --check-cmd 'bash docs/plans/pipeline-r1/check.sh'` was refused before it ran, so the operator had to deviate from the given command.
- Cause (verified): The worktree-isolated agent's command guard refuses a command string embedded in arguments, because it cannot prove the string is not git. The refusal said "runs harness with the text bash docs/plans/pipeline-r1/check.sh". Shell variables (`J=...; python3 $J`) were refused for the same reason.
- Fix: Used `--check docs/plans/pipeline-r1/check.sh`. The job's check.sh is byte-identical to the plan's (`diff`: SAME).
- Prevent: In job plans and operator prompts, prefer `--check FILE` over `--check-cmd 'CMD'`. In isolated agents, use literal paths instead of shell variables.
- Seen: 2026-10-08, pipeline-r1 job creation.

## L24. The worker's offline uv cache was not ready in the sandbox   [who: codex] [area: codex-cli]
- Problem: In round 1, the worker spent time building a temporary uv cache. The default cache was denied, and the first copy lacked a transitive dependency.
- Cause (verified, from worker HANDOFF round 1): the sandbox denied ~/.cache/uv/sdists-v9/.git. soundfile 0.14.0 needs typing-extensions 4.16.0, which the first copied set omitted. The worker left /private/tmp/pipeline-r1-uv-cache behind.
- Fix: The worker built a writable cache at /private/tmp/pipeline-r1-uv-cache from installed archives, including the transitive dependency.
- Prevent: This extends L14. For uv projects, task.md gives a ready writable `UV_CACHE_DIR` (pre-populated by the orchestrator) plus `UV_OFFLINE=1`. Delete the temporary cache after the job.
- Seen: 2026-10-08, pipeline-r1 round 1.

## L25. Two operators rewrote the shared OPERATOR_HANDOFF.md   [who: claude] [area: harness]
- Problem: pipeline-mockups operator created .harness/OPERATOR_HANDOFF.md with its section; the pipeline-r1 operator later rewrote the whole file with its own sections, and the pipeline-mockups section was lost (re-appended by hand).
- Cause (verified): one file per project shared by parallel operators, each writing it whole (Write/overwrite) rather than editing only its own section; seen by `grep "^# " .harness/OPERATOR_HANDOFF.md` showing only pipeline-r1 content after their update.
- Fix: re-appended the pipeline-mockups section at the end, under its own top-level heading.
- Prevent: one handoff file per job (e.g. `.harness/jobs/<job>/OPERATOR_HANDOFF.md`), or operators only append/edit their own section; enforce in the codex-harness skill / README.
- Seen: 2026-10-08, pipeline-mockups + pipeline-r1 in parallel.

## L26. `harness new` silently runs init and creates AGENTS.md outside the job scope   [who: claude] [area: harness]
- Problem: operator was told not to run `harness init` if .harness/ exists; it did not exist, and `harness new` auto-initialised it, creating an untracked AGENTS.md at the repo root (with the "Lessons and multi-model work" section) during a job whose scope was docs/design/mockups/ only.
- Cause (verified): harness.py `cmd_new` calls `cmd_init` when HDIR is missing; `ensure_agents_sections` creates AGENTS.md if absent.
- Fix: reported in orchestrator_review.md as a non-worker change.
- Prevent: orchestrator runs `harness init` once (and decides on AGENTS.md / commits it) before launching parallel operators; or `harness new` should refuse / warn instead of auto-init. Also two parallel operators can both hit init at the same time.
- Seen: 2026-10-08, pipeline-mockups.

## L27. `harness lessons` drops the worker's lessons when they use ### sub-headings   [who: claude] [area: harness]
- Problem: retro.md shows "Worker's Lessons (draft): (none)" although HANDOFF.md has a `## Lessons (draft)` section with entries P1 and P2.
- Cause (verified): harness.py line ~620 regex `^#+\s*Lessons \(draft\)\s*\n(.*?)(?=^#+\s|\Z)` stops at the next heading of ANY level, so the first `### P1.` ends the match with an empty body.
- Fix: `lessons_section()` stops only at a heading of the same or higher level; tests/test_lessons_section.py; verified on pipeline-mockups retro (worker P1 now appears).
- Prevent: stop only at a heading of the same or higher level (e.g. `(?=^#{1,2}\s|\Z)`), and add a stub test with `###` entries.
- Seen: 2026-10-08, pipeline-mockups retro.md.

Note (2026-10-08, pipeline-r1): `harness lessons` also loses worker drafts when HANDOFF.md is rewritten in a later round; saving rounds/<n>/HANDOFF.md would keep them (see L27 for the regex part).

## L28. Task named an API endpoint that does not work on this machine   [who: claude] [area: process]
- Problem: job run-openthai coded against Ollama `POST /v1/systemone`; on this Mac (Ollama 0.40.1) the model
  answers "does not support decision", so the runner needs another round for OpenThai's own server on :8000.
- Cause (verified): the endpoint came from a web-research note (Codex, read-only) and from the model page; nobody
  called it locally before task.md was written. `ollama show` lists only tools / thinking / completion.
- Fix: install OpenThai's Python server (`uvicorn openthai_systemone.server:app --port 8000`), point the runner's
  url there.
- Prevent: before a task.md depends on an external API / runtime, the orchestrator smoke-tests one real call on
  the target machine (the Laya smoke test before its job would have been the same habit); research notes are
  hypotheses until a local call succeeds.
- Seen: 2026-10-08, decision-model eval (run-openthai).

## L29. A language-share check pushed the worker to add answer-giving text   [who: claude] [area: harness check / evals]
- Problem: decision-cases round 1 passed its check, but all 8 context_retention_mixed states (and agent_routing_mixed_007/008, network_level_mixed_001/005, agent_routing_th_002) ended with an added Thai sentence that stated the answer ("...จึงไม่จำเป็นต้องเก็บ...").
- Cause (verified): the check forced Thai >= 15% (mixed) / >= 50% (th) of letters but did not forbid commentary; the worker met the share by adding Thai text (its HANDOFF lesson: "enough Thai task context to meet the language-share rule"), placed after the English tool excerpt, and that text explained the label. The orchestrator wrote the check.
- Fix: round 2 feedback + a tighter check ('Tool output:' line English-only, verdict-word list); the worker removed every verdict; 24/24 excerpts verbatim, check PASS.
- Prevent: a check that forces a language share (or any surface property) must also forbid the easy way to satisfy it: verdict/explanation words in the state, translated tool output; the operator greps states for answer hints before recommending accept, because a word list catches only part of them (2 of ~13 here).
- Seen: 2026-10-08, decision-cases rounds 1-2 (agent-kit).
