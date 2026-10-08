# agent-kit handoff

Log for kit / tooling work (mods, harness, installer, global rules). Project work (e.g. npd-comparables) is logged in
that project's session log, which only points here. Live sources on the original machine: `~/tools/claude-mods`,
`~/tools/codex-harness`, `~/.claude/CLAUDE.md`, `~/.claude/skills/`, `~/.codex/AGENTS.md`; copy them into the kit
with `./sync-from-this-machine.sh`, then commit here.

## Status (rewrite in place)

2026-10-08 ~19:00, nothing running. Principles recorded (design.md s.0): ultimate goal = Orca-like harness for data
analytics, human pace, understanding first, truth over agreement (also in global CLAUDE.md / AGENTS.md). Research
(Codex gpt-6.1-sol low, web): docs/research/{context-tools-oss,mods-vs-mechanisms,typesafe-ai}.md + index.md.
Job io-index drafted in .harness/drafts/io-index (task.md, check.sh, fixture) but PARKED: Claude pushed back (index not
needed yet; work order puts it 4th). NEXT: user answers Open 1-3, then draft task for work-order step 1 (`access` /
network per job in harness) and show the scope before creating the job. Push still blocked: GitHub repo missing.

(previous) 2026-10-08 late night. Shared skills `handoff` + `wiki` in `agent-kit/skills`, linked into ~/.claude/skills and
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

1. Research D (Orca + deepseek-harness ideas) and E (decision models vs TypeSafe) by Codex: save to docs/research,
   summarise once for the user (understanding section: what it means for us, verified vs hypothesis).
2. Work-order step 1: draft task for `access` / network per job in harness (design 5.1); show the user the scope
   before creating the job; one job at a time.
3. Then: `harness --worker claude`; bounded review packets with the understanding section.
4. Skill sets A: `skills/<set>/<name>` (core, data, design later) + `install.sh --sets`; skill token monitor (per skill:
   description tokens loaded each session + times used, from /context numbers or SKILL.md frontmatter + io-log
   `skills` field). Scope with the user first.
5. Open questions from Codex research (not answered yet): reset threshold (60-70%?), output budget (4-8k chars?),
   routing model; external classifier: Claude advised no (company data).

## Backlog

- io-index (Decision io-log-store B): drafted in .harness/drafts/io-index (task.md, check.sh, fixture). Before
  running: make check.sh faster (dry run did not finish in >5 min) and prove it fails before the work.

## Decisions

- Decision: human-pace | Choice: the harness keeps a pace the user can follow (one active job by default, short review packets that explain the new code, no new round before review); speed is a setting, not the goal | By: user | Note: design.md section 0
- Decision: next-step | Choice: work-order step 1 (`access` / network per job in harness) next; io-index moved to the backlog | By: user
- Decision: skill-sets-final | Choice: A (folders per set + `install.sh --sets`), replaces B; plus monitoring of how many tokens each skill / set costs | By: user | Note: design skills cost ~2.3k tokens (claude.ai sync) + ~0.7k (design plugin) per session, measured from /context
- Decision: orca-scope | Choice: Orca + ideas from github.com/deepseek-ai/deepseek-harness (research task D running) | By: user
- Decision: decision-models | Choice: compare TypeSafe Jev with iapp-technology/openthai-systemone, ipenywis/laya-ultrafast, Cloudflare CLEF decision models before any pilot (research task E running) | By: user
- Decision: push | Choice: done by the user; origin/main = c12f9aa verified with git fetch | By: user
- Decision: truth-over-agreement | Choice: never invent data; do not agree to please, push back with evidence (own earlier proposals included) | By: user | Note: in global CLAUDE.md + AGENTS.md
- Decision: understanding-first | Choice: results count only when the user can explain them (BU context, data source, method choice and fit, strength of evidence, the code); choices explained as comparisons; review packets carry an understanding section | By: user | Note: design.md section 0
- Decision: objective | Choice: 1) context size, 2) subscription quota; total tokens / money after | By: user
- Decision: skill-sets | Choice: B (each set a local Claude plugin enabled per project; per-set links for Codex) | By: user
- Decision: work-order | Choice: 1) access / network per job in harness 2) --worker claude 3) bounded review packets 4) io-log index (scope approved, job io-index) | By: user
- Decision: ultimate-goal | Choice: an Orca-like harness for data analytics / data science: per-agent network on/off, Claude and Codex working together, small context / token use | By: user | Note: recorded in docs/design.md section 0
- Decision: models | Choice: Claude + Codex only for now (the two the user uses); design stays role-agnostic so either can orchestrate or work | By: user
- Decision: worker-network | Choice: approved (requests in 4 levels, planning round + per-job budget); access is set per job scope, not per model | By: user
- Decision: caps | Choice: CLAUDE.md / AGENTS.md <= 120 lines, skill description <= 300 chars | By: user
- Decision: triangulation | Choice: no tolerance; user reviews both results side by side | By: user

- Decision: separate-kit-npd | Choice: A (move tooling entries out of the npd session log into this file) | By: user
- Decision: transport | Choice: GitHub private repo, user pushes | By: user
- Decision: identities | Choice: projects_cj = company email, everything else = gmail; kit history rewritten | By: user

Decision: io-log-store | Choice: B (JSONL source + incremental SQLite index) | By: user | Note: the log may move elsewhere later, and JSONL is not a good migration format: keep the SQLite schema clean and versioned (real columns, documented) and give it an export, so a move copies the table, not the JSONL
- Decision: npd-template | Choice: delete npd's /handoff skill, npd uses the template hooks; check it works the same | By: user | Note: done 2ea64c1
- Proposal: skill-sets | Options: A) folders per set (core, data, design) + `install.sh --sets` B) each set a local Claude plugin enabled per project (data projects do not load design skills) + per-set links for Codex | Recommend: B | Rationale: user wants sets because design and data/analytics skills differ; per-project enable also saves tokens

## How to verify

- `claude plugin list | grep clear-guard` (enabled, 0.2.0), `claude plugin test ~/tools/claude-mods/clear-guard` (9 pass), `.../wiki-note` (8 pass)
- `python3 -m unittest discover -s tests` (15 OK); `python3 project-template/.claude/skills/wiki/wiki_lint.py --dir <wiki>`
- `./install-project.sh <dir> --dry-run` lists what a project would get
- `./install.sh --dry-run` lists the planned copies / links
- `git -C ~/agent-kit log --format=%ae | sort -u` = gmail only
