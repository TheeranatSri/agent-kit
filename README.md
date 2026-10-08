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
| `claude-mods/` | clear-guard mod: asks before `/clear` when the project's session log is stale (path from the project's `.claude/handoff.json`); wiki-note mod: `/note <kind>: <title> [-- details]` appends to the wiki `log.md`, status line shows handoff age + last wiki log date; local plugin marketplace |
| `skills/` | shared skills `handoff`, `wiki` (+ `wiki_lint.py`): linked into `~/.claude/skills` and `~/.codex/skills`, so Claude and Codex read the same files |
| `project-template/` | per-project kit: SessionStart / SessionEnd hooks, `.claude/handoff.json`, wiki seed (`index.md`, `log.md`, `lessons.md`), rules section for CLAUDE.md |
| `install-project.sh` | adds `project-template/` to a project (`--wiki-dir`, `--session-log`, `--update`, `--dry-run`); never replaces your files unless `--update` |
| `tests/` | `python3 -m unittest discover -s tests` (installer, hooks, wiki lint) |
| `claude-home/` | global `CLAUDE.md` (Claims, roles, handoff, structured lines) and user skills |
| `codex-home/` | global `AGENTS.md` for Codex |
| `optional/agent-io-log/` | logs prompts/answers + structured lines to `~/agent-io-logs/`; installed only with `--with-io-log` |
| `install.sh` | idempotent installer (`--dry-run`, `--with-io-log`); backs up, never deletes |
| `SETUP.md` | the steps Claude follows |
| `sync-from-this-machine.sh` | on the original machine: copy the live files into the kit (files only, not history) before committing |

## Updating

- Original machine: `./sync-from-this-machine.sh`, review `git status`, commit, push.
- Other machines: `git pull && ./install.sh`.
