# SETUP: instructions for Claude Code on a new machine

The user cloned this repo and said "set up from SETUP.md" (or similar). Follow these steps in order. Ask before
anything not listed here. Reply to the user in Thai; keep commands and paths as they are.

## 0. Before you start

- Where is the kit? It is the folder this file is in (expected `~/agent-kit`). If it is elsewhere, every path below
  is relative to that folder; `install.sh` finds itself.
- Ask the user one question: **install the optional agent-io-log hooks?** (they log every prompt/answer to
  `~/agent-io-logs/`; separate from the rest, off by default).

## 1. Dry run, show the user

```bash
cd ~/agent-kit && ./install.sh --dry-run            # add --with-io-log if the user said yes
```

Show the user the list of what will be copied, linked and backed up. Existing files that differ are moved to
`<file>.bak-<timestamp>`, never deleted. Get an OK.

## 2. Install

```bash
./install.sh                                         # add --with-io-log if the user said yes
```

What it does:

| Item | Goes to | How |
|---|---|---|
| codex-harness (harness CLI, LESSONS.md, overview page) | `~/tools/codex-harness` | symlink to the kit, so `git pull` updates it |
| claude-mods (clear-guard mod + local marketplace) | `~/tools/claude-mods` | symlink |
| `harness` command | `~/.local/bin/harness` | symlink to `harness.py` |
| global rules for Claude | `~/.claude/CLAUDE.md` | copy |
| user skills: codex-harness, bq-readonly-pull, excel-review-workbook, paid-run-gate | `~/.claude/skills/<name>/` | copy |
| global rules for Codex | `~/.codex/AGENTS.md` | copy |
| node for hooks (lesson L16) | `~/.local/bin/node` | symlink to the newest nvm node, if no node link yet |
| Claude Code plugins | `codex@openai-codex`, `clear-guard@local-mods` (user scope) | `claude plugin install` |
| optional agent-io-log | `~/tools/agent-io-log` + 3 hooks in `~/.claude/settings.json` | only with `--with-io-log` |

## 3. Verify and report

Read the `== checks` part of the output. Expected:

- `ok: harness --help`
- `ok: ~/.local/bin on PATH` (if WARN: tell the user the exact line to add to their shell profile)
- `clear-guard@local-mods` and `codex@openai-codex` listed; clear-guard tests `5 pass`
- every prerequisite `ok` (if `MISSING: codex` or `node`: tell the user, do not install it yourself)

Then tell the user to start a new Claude Code session (or `/reload-plugins`). Write each result as
`Done: ... | Verified: ...` or `Failure: ...` lines (the rules in `~/.claude/CLAUDE.md`, now installed).

## 4. Things the kit does NOT do (tell the user if relevant)

- No secrets: Codex login (`codex login`), gcloud auth, `.env` files stay per machine.
- `~/.claude/settings.json` is not replaced (only the optional io-log hooks are added to it).
- Skills `bq-readonly-pull`, `excel-review-workbook`, `paid-run-gate` point at the npd-comparables project under
  `~/Documents/projects_cj/npd-comparables`; they only matter on a machine that has that project.
- Project files (each project's CLAUDE.md / AGENTS.md / lessons / `.claude/` hooks) come with that project's repo.

## Updating later

- On this machine: `cd ~/agent-kit && git pull && ./install.sh`. Tools in `~/tools` are symlinks, so harness,
  LESSONS.md and clear-guard update with `git pull` alone; CLAUDE.md, skills and AGENTS.md are copies and need
  `./install.sh` (it backs up a local version that changed).
- A lesson written on this machine goes into `~/tools/codex-harness/LESSONS.md` = the kit: commit and push it from
  `~/agent-kit`.
