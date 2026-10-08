# agent-kit handoff

Log for kit / tooling work (mods, harness, installer, global rules). Project work (e.g. npd-comparables) is logged in
that project's session log, which only points here. Live sources on the original machine: `~/tools/claude-mods`,
`~/tools/codex-harness`, `~/.claude/CLAUDE.md`, `~/.claude/skills/`, `~/.codex/AGENTS.md`; copy them into the kit
with `./sync-from-this-machine.sh`, then commit here.

## Status (rewrite in place)

2026-10-08 late night. Shared skills `handoff` + `wiki` in `agent-kit/skills`, linked into ~/.claude/skills and
~/.codex/skills (Codex lists both); mod `wiki-note` (/note + status line) built, tested 8/8, installed. Open: SQLite
for the io-log (Proposal io-log-store), npd handoff skill name clash. Next: user reviews; then design step 1 caps
check / step 3.

(previous) 2026-10-08 night. Next items 2-4 done (user asked): clear-guard reads `.claude/handoff.json` (0.2.0, 9/9 tests),
`project-template/` + `install-project.sh` (handoff skill + hooks, /wiki skill + wiki_lint.py, wiki seed), 15/15 kit
tests. npd-comparables NOT changed (it works with the defaults). Next: user reviews; then design step 2 (shared skills).

(previous) 2026-10-08 evening. docs/design.md reviewed and decided. Next: step 2 (shared skills in agent-kit/skills, linked for Claude and Codex, test with Codex) in a NEW session.

(previous) 2026-10-08 ~15:30. Kit built and committed (no push yet: SSH keys made, user adds them on GitHub / may regenerate
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
| clear-guard 0.2.0: log glob + staleMin from the project's `.claude/handoff.json` (default unchanged; a broken config never blocks `/clear`); 9/9 tests | `~/tools/claude-mods` (09afb16), synced to `claude-mods/` |
| Project template: `.claude/handoff.json` (shared config), generic `/handoff` skill, SessionStart / SessionEnd hooks reading the config (`handoff_config.sh`), `/wiki` skill (query / ingest / lint) + `wiki_lint.py` (stdlib; 0 errors on the npd wiki after 3 rules were loosened to match it), wiki seed `index.md` / `log.md` / `lessons.md`, rules section for CLAUDE.md / AGENTS.md | `project-template/`, `install-project.sh`, `tests/test_project_template.py` (15 tests), README + SETUP "New project" |
| Shared skills `handoff`, `wiki` (+ `wiki_lint.py`) moved from project-template to `skills/`; install.sh links them for Claude and Codex; linked on this machine by hand (install.sh would replace this machine's live folders) | `skills/` (18d6fd6); Claude lists `wiki`, `codex exec` lists `handoff` + `wiki` |
| wiki-note mod: `/note <kind>: <title> [-- details]` appends `## [date] kind | title` to the wiki log.md (local date, UTC+7 checked); status line `handoff 12m · wiki 2026-10-07 (37)`, refreshed each minute, `stale` past staleMin; installed user scope | `~/tools/claude-mods/wiki-note` (e861c0d), synced |
| io-log storage benchmark (JSONL vs SQLite on the real log x1/x10/x100) | `docs/research/io-log-storage.md`, `optional/agent-io-log/bench_storage.py` |
| Two git identities: gmail by default, company email + `~/.ssh/id_ed25519_cj` under `~/Documents/projects_cj/` (`includeIf`); kit history rewritten to gmail (old in local tag `backup/before-email-rewrite`) | `~/.gitconfig` (backup `.bak-20261008-145721`), `~/.gitconfig-cj`, `~/.ssh/config` |

## Next

1. User: add the public keys on GitHub (or regenerate keys themselves with a passphrase), then
   `ssh -T git@github.com` and `cd ~/agent-kit && git push -u origin main`.
2. Open (ask first, lesson L10): (a) Proposal io-log-store (see Decisions); (b) npd-comparables has a project
   skill `handoff` with the same name as the shared one, so Claude shows only one: delete npd's copy (the shared one
   does the same with the default paths) and move npd onto the template hooks (`install-project.sh --update`);
   (c) `origin:` frontmatter on skills (design step 2) not added yet: check first that Codex accepts extra keys.
3. Agent brain (Proposal agent-brain, awaiting A/B): shared skills in agent-kit/skills linked into ~/.claude/skills and ~/.codex/skills; close the lesson loop (each lesson names the skill/check it changed, count Seen-again); harness --worker codex|claude + ORCHESTRATOR skill; then triangulate, 4-level requests, planning round + budget. Write docs/design.md first.
4. After each change: tests (`claude plugin test`, `python3 -m unittest discover -s tests`), `/reload-plugins`, `./sync-from-this-machine.sh`, commit here.

## Decisions

- Decision: models | Choice: Claude + Codex only for now (the two the user uses); design stays role-agnostic so either can orchestrate or work | By: user
- Decision: worker-network | Choice: approved (requests in 4 levels, planning round + per-job budget); access is set per job scope, not per model | By: user
- Decision: caps | Choice: CLAUDE.md / AGENTS.md <= 120 lines, skill description <= 300 chars | By: user
- Decision: triangulation | Choice: no tolerance; user reviews both results side by side | By: user

- Decision: separate-kit-npd | Choice: A (move tooling entries out of the npd session log into this file) | By: user
- Decision: transport | Choice: GitHub private repo, user pushes | By: user
- Decision: identities | Choice: projects_cj = company email, everything else = gmail; kit history rewritten | By: user

Proposal: io-log-store | Options: A) SQLite only B) JSONL source + incremental index.db C) keep JSONL | Recommend: B | Rationale: reports 100x faster at a year of data, JSONL stays greppable and the db can be rebuilt; write cost +1.5 ms per hook is negligible

## How to verify

- `claude plugin list | grep clear-guard` (enabled, 0.2.0), `claude plugin test ~/tools/claude-mods/clear-guard` (9 pass), `.../wiki-note` (8 pass)
- `python3 -m unittest discover -s tests` (15 OK); `python3 project-template/.claude/skills/wiki/wiki_lint.py --dir <wiki>`
- `./install-project.sh <dir> --dry-run` lists what a project would get
- `./install.sh --dry-run` lists the planned copies / links
- `git -C ~/agent-kit log --format=%ae | sort -u` = gmail only
