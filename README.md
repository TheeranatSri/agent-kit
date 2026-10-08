# agent-kit

Everything needed to work as **user → Claude Code (orchestrator) → Codex (worker)** on a new machine that has only
Claude Code and Codex installed.

## On a new machine

```bash
git clone <this repo> ~/agent-kit
cd ~/agent-kit && claude
```

Then tell Claude: **"ทำตาม SETUP.md"** (set up from SETUP.md). Claude runs a dry run, shows you what changes, then
installs and verifies.

## What is inside

| Folder | What |
|---|---|
| `codex-harness/` | `harness` CLI (Codex as a worker, human review every round), `LESSONS.md`, `docs/harness-overview.html` |
| `claude-mods/` | clear-guard mod: asks before `/clear` when the project's session log is stale; local plugin marketplace |
| `claude-home/` | global `CLAUDE.md` (Claims, roles, handoff, structured lines) and user skills |
| `codex-home/` | global `AGENTS.md` for Codex |
| `optional/agent-io-log/` | logs prompts/answers + structured lines to `~/agent-io-logs/`; installed only with `--with-io-log` |
| `install.sh` | idempotent installer (`--dry-run`, `--with-io-log`); backs up, never deletes |
| `SETUP.md` | the steps Claude follows |
| `sync-from-this-machine.sh` | on the original machine: copy the live files into the kit before committing |

## Updating

- Original machine: `./sync-from-this-machine.sh`, review `git status`, commit, push.
- Other machines: `git pull && ./install.sh`.
