# agent-kit handoff

Log for kit / tooling work (mods, harness, installer, global rules). Project work (e.g. npd-comparables) is logged in
that project's session log, which only points here. Live sources on the original machine: `~/tools/claude-mods`,
`~/tools/codex-harness`, `~/.claude/CLAUDE.md`, `~/.claude/skills/`, `~/.codex/AGENTS.md`; copy them into the kit
with `./sync-from-this-machine.sh`, then commit here.

## Status (rewrite in place)

2026-10-08 ~15:30. Kit built and committed (no push yet: SSH keys made, user adds them on GitHub / may regenerate
them). Next: mod changes driven by use cases found while working in npd-comparables.

## Done

| What | Where |
|---|---|
| clear-guard mod: `/clear` asks first when the newest `notebooks/knowledge/session-log-*.md` is >30 min old (`/clear force` skips; no folder = not guarded); 5/5 tests; installed user scope as `clear-guard@local-mods` | `~/tools/claude-mods/clear-guard` (6cd9561) |
| Codex plugin hook error `node: command not found`: symlink `~/.local/bin/node` -> nvm v24.21.0 | lesson L16, `~/tools/codex-harness` (038a3d1) |
| harness overview page: clear-guard + handoff hooks, new-machine setup, L16, comparison with Orca (stablyai/orca) | `docs/harness-overview.html` (f763fba, 55feb4c); https://claude.ai/artifact/TqWopdKeyhpaABLygWJQjk |
| agent-kit repo: harness, LESSONS, clear-guard, global CLAUDE.md / AGENTS.md, 4 user skills, optional agent-io-log, `install.sh` (tested in a fake HOME, idempotent), `SETUP.md` for Claude, sync script (file copy) | `~/agent-kit`; remote `git@github.com:TheeranatSri/agent-kit.git` |
| Research notes (Sonnet, sources checked): LLM wiki (Karpathy gist 2026-04-04) and Orca (stablyai/orca) | `docs/research/llm-wiki.md`, `docs/research/orca.md` |
| Design draft for review: roles per job (Claude / Codex, Gemini later), token budget, shared brain, harness adapters, data requests | `docs/design.md`; token report `optional/agent-io-log/token_report.py` |
| Two git identities: gmail by default, company email + `~/.ssh/id_ed25519_cj` under `~/Documents/projects_cj/` (`includeIf`); kit history rewritten to gmail (old in local tag `backup/before-email-rewrite`) | `~/.gitconfig` (backup `.bak-20261008-145721`), `~/.gitconfig-cj`, `~/.ssh/config` |

## Next

1. User: add the public keys on GitHub (or regenerate keys themselves with a passphrase), then
   `ssh -T git@github.com` and `cd ~/agent-kit && git push -u origin main`.
2. Mod use cases from npd work. Candidate: clear-guard reads the log location from a per-project config
   (e.g. `.claude/clear-guard.json`) instead of the hardcoded `notebooks/knowledge/session-log-*`.
3. Put the generic `/handoff` skill and SessionStart / SessionEnd hooks (now in npd-comparables `.claude/`) into
   `agent-kit/project-template/`; npd keeps its own copy.
4. Knowledge wiki (Proposal knowledge-wiki-v2, awaiting user A/B): index.md + log.md in notebooks/knowledge (no file moves), CLAUDE.md rule, /wiki skill (ingest/query/lint), mod /note + status line; generic, template in the kit.
5. Agent brain (Proposal agent-brain, awaiting A/B): shared skills in agent-kit/skills linked into ~/.claude/skills and ~/.codex/skills; close the lesson loop (each lesson names the skill/check it changed, count Seen-again); harness --worker codex|claude + ORCHESTRATOR skill; then triangulate, 4-level requests, planning round + budget. Write docs/design.md first.
6. After each change: tests, `/reload-plugins`, `./sync-from-this-machine.sh`, commit here.

## Decisions

- Decision: models | Choice: Claude + Codex only for now (the two the user uses); design stays role-agnostic so either can orchestrate or work | By: user
- Decision: worker-network | Proposed: request -> human approve -> harness fetches (4 risk levels), plus a planning round + per-job data budget; awaiting user

- Decision: separate-kit-npd | Choice: A (move tooling entries out of the npd session log into this file) | By: user
- Decision: transport | Choice: GitHub private repo, user pushes | By: user
- Decision: identities | Choice: projects_cj = company email, everything else = gmail; kit history rewritten | By: user

## How to verify

- `claude plugin list | grep clear-guard` (enabled), `claude plugin test ~/tools/claude-mods/clear-guard` (5 pass)
- `./install.sh --dry-run` lists the planned copies / links
- `git -C ~/agent-kit log --format=%ae | sort -u` = gmail only
