# agent-io-log

Raw event log of Claude Code and Codex work. Local only, stdlib only, no network, **zero LLM calls** (hooks only copy and regex-parse files, so logging costs no tokens).

## Layout
`~/agent-io-logs/<YYYY-MM-DD>/<project-slug>.jsonl` - one JSON event per line. Filter by `branch` / `worktree` fields. State: `~/agent-io-logs/_state.json` (byte offset per source file, so nothing is written twice). Errors: `~/agent-io-logs/_errors.log`.

## Events
user_input, assistant_output, agent_prompt (orchestrator -> agent), agent_report (agent -> orchestrator; task-notification/peer messages in the main file are also logged as agent_report), tool_rejected, codex_input, codex_output.

Common fields: ts, event, project, branch, worktree, session, actor (main | agent:<description> | codex:<job or session>), turn, from, to, text (full), model, usage, duration_s, permission_mode, parent, agent_id, source {file, uuid, line}.
Output events add: tools[] {name, description, input, result (full), is_error, rejected}, skills[] {name, description from SKILL.md}, agents_spawned[], files_changed[], commits[], and the structured-line fields claims, proposals, decisions, questions, assumptions, failures, done, checks (parsed with regex from the lines in ~/.claude/CLAUDE.md "Structured lines"; unparsed parts go to `raw`).
A turn = one input and everything the actor produced until the next input.
Thinking blocks are never logged. Tool results are logged in full (size to be evaluated later).

## How it runs
Hooks in `~/.claude/settings.json`: UserPromptSubmit, Stop, SubagentStop run `python3 agent_io_log.py hook` (exit 0 always, 30s timeout). Stop also ingests new Codex rollouts from ~/.codex/sessions (touched in the last 24h). The still-open turn is re-read on the next run; Stop/SubagentStop close it.

## Backfill / rerun
`python3 agent_io_log.py --backfill [--since YYYY-MM-DD]` (idempotent; a second run appends 0).

## Disable
Remove the three entries whose command contains `agent_io_log.py` from `hooks` in `~/.claude/settings.json`, or restore the backup `~/.claude/settings.json.bak-<timestamp>`. Logs already written stay.
