# Orca research (2026-10-08)

## Candidates
1. **Orca (stablyai/orca)** - best fit. https://github.com/stablyai/orca , site https://www.onorca.dev/
   - Maker Stably AI; MIT; Electron/TypeScript desktop "agent development environment" + iOS/Android companion. Created 2026-03-17, pushed 2026-10-08, 87.4k stars, 5.6k forks, release v1.4.222 (2026-10-07) (GitHub API https://api.github.com/repos/stablyai/orca , .../releases/latest).
   - Runs Claude Code, Codex and 25-40 other CLI agents in parallel, each in its own git worktree; fan one prompt to N agents, compare, merge winner; inline diff annotation sent back to agents; GitHub/Linear integration; notifications/unread state; BYO subscription (no API interception). (README, onorca.dev)
   - Orchestration (coordinator/worker): CLI primitives `terminal list/send/wait`; maintainer announced "experimental orchestration" as an installable skill (May 2026): threaded messages, ask/reply, task dispatch, worker_done/escalation waits, task DAGs, decision gates, coordinator loop. Coordinator is typically an agent (e.g. Opus); workers run in worktrees. https://github.com/stablyai/orca/discussions/681 ; skill listing https://mcpservers.org/agent-skills/stablyai/orchestration (third-party listing; internals unverified).
   - Human in loop: user reviews diffs, annotates, commits in the app; mobile steering. Memory/learning loop: none found (unverified). Cost: user's own subscriptions; usage/agent-time tracking mentioned, privacy details unverified (onorca.dev).
2. **claude-codex-orchestrator (`cco`)** https://github.com/Gabriel-Dalton/claude-codex-orchestrator - MIT, 0 stars, 5 commits, Python 3.11+. Claude Code skill+CLI: Claude writes the brief, Codex agents run in Orca terminals in assigned folders, tool captures changed files + report, Claude reviews and sends follow-ups. State in local `agents.json` outside the repo. Closest in spirit to the user's setup, but tiny.
3. **orca-cli/orca** https://github.com/orca-cli/orca - MIT, Go single binary, SQLite run state, worktrees, MCP server, review queue queued->running->ready->shipped, human runs `orca ship` to open PR; 4 stars, pre-v1.0. Runs Claude Code, Codex, Aider.
4. **fmfsaisai/orca** https://github.com/fmfsaisai/orca - MIT, tmux + skills, lead agent dispatches to workers (Claude or Codex either role), workers can propose plans; 8 stars, 90 commits.
- Related but different name: Orka (Mr-Neutr0n/orka, Dusttoo/orka) - Jira ticket orchestration with review gates. Not Orca.

Fit: stablyai/orca is the real "Orca" (by far the most used); the others share the name only.

## Comparison
| | Orca (stablyai) | Ours (codex-harness) |
|---|---|---|
| Purpose | GUI workspace to run many agents in parallel | Controlled delegation of one job to Codex with review |
| Orchestrates | User, or optional coordinator agent (experimental skill) | Main Claude session; Opus operator runs CLI |
| Executes | Any CLI agent (Claude, Codex, 30+) | Codex gpt-6.1-sol only |
| Parallelism | Many agents/worktrees at once, fan-out and compare | One worker per job, sequential rounds |
| Isolation | git worktree per agent; sandbox is the agent's own | Codex workspace-write sandbox, no network, `--scope` paths |
| Human review | Diff view/annotate, mobile; optional, user-driven | Mandatory every round (accept/feedback/reject) |
| Commit policy | User commits in app; agents may commit (agent-dependent, unverified) | Only main Claude commits; harness never does |
| State/handoff | Worktrees, terminal scrollback, unread state; DAG in orchestration skill | HANDOFF.md every layer, state.json, rounds/, commands.log |
| Learning loop | None found | LESSONS.md Prevent lines injected into next prompt; retro per job |
| Data access | Agents use own network/tools | No network; data_requests, SQL checked, human approves |
| Setup | Desktop app (Electron), MIT, free | One stdlib Python file |
| Maturity | 87k stars, daily releases | Personal tool, tested on a few jobs |
| Best fit | Many parallel tasks, compare agents | Audit-heavy data work with controlled blast radius |

## Could borrow
- Worktree per job (instead of shared scope paths) to run several Codex jobs in parallel.
- Diff annotation: line-level feedback into `harness feedback`.
- Three-state wait (done / waiting for input / stuck) as in discussion #681; ours has needs_input but no "unresponsive" detection beyond stale HANDOFF age.
- Notifications/mobile ping (we have macOS notification via monitor).
- Task DAG for splitting a large job into dependent sub-jobs.

## Deliberately different
- Human decides every round; no autonomous coordinator merging.
- Single committer (main session); worker never commits.
- No network for worker; data pulled only after human approves SQL.
- Lessons with Prevent lines feed back automatically; Claim/Check lines are auditable.
- Zero dependencies and file-based state, easy for any model to take over.
