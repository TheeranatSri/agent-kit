# agent-kit design: multi-model work for data analytics, with a human review loop

Status: reviewed by the user 2026-10-08 (sections 5, caps, triangulation decided). Decisions so far are marked **Decided**; the rest are proposals.
Research behind it: `docs/research/llm-wiki.md`, `docs/research/orca.md`, `docs/research/wikiskill.md`.

## 0. Principles

- **Ultimate goal (user, 2026-10-08): an Orca-like harness for data analytics / data science.** Like Orca
  (stablyai/orca, `docs/research/orca.md`): several agents side by side, each in its own session / worktree, one
  place to watch and review them. Different from Orca: built for data work (numbers, tables, claims, Check lines,
  data requests), per-agent settings that decide which agent may use the network and which may not (5.1), and
  Claude and Codex working together in the same harness (either can orchestrate or work, section 3). Context and
  token use must stay small (section 1, `docs/research/mods-vs-mechanisms.md`).
- **Roles are per job, not per model.** Any model can orchestrate or work: Claude Code, Codex CLI today; Gemini
  CLI or others later through an adapter. Nothing in the kit assumes "Claude orchestrates, Codex works".
  **Decided** (user): Claude + Codex now, design stays open for Gemini.
- **The brain lives in files, not in a model:** skills (how), memory (what / where), logs (what happened). Every
  model reads the same files.
- **Human decides every round.** Automated loops only where a deterministic check exists; quality of results
  (e.g. top-3 similar items) is judged by the user, never by an LLM judge. **Decided**.
- **Data work, not app dev:** outputs are numbers, tables, claims; correctness = right data, reconciled totals,
  sound method, conclusions no stronger than the evidence (Check lines).
- **Token budget is a design constraint** (section 1). **Decided** (user: we are not Google).

## 1. Token budget

What costs tokens (measured 2026-10-08 with `token_report.py`, Claude only; Codex turns are not metered in the log):

| actor | turns | output | cache_read | cache_write |
|---|---|---|---|---|
| main session (Opus) | 218 | 572k | 191.1M | 1.6M |
| all subagents | 89 | 223k | 56.5M | 6.1M |

Claim: the main session's long context dominates cost (77% of cache reads), not subagents | Status: verified (one
day) | Evidence: `python3 ~/tools/agent-io-log/token_report.py --since 2026-10-08 --by actor`.

Tool calls are tracked too (Claude and Codex, from the same log): `token_report.py --tools` gives calls, errors,
rejections and result characters per tool and actor kind. Result characters are what a call adds to the context, so
big readers (a 6 MB `codex.log`, a full YAML, a PDF) show up here. The job's `access` (5.1) decides which tools a
run may have; the log shows which it actually used.

Rules:
1. Always-loaded context is pointers only (CLAUDE.md / AGENTS.md say where to look); details load on demand.
2. Index first: wiki `index.md`, `semantic/cookbook.md`, lessons index, skill list.
3. Right model for the job: the orchestrator decides and relays; reading / searching / drafting goes to a cheaper
   model; subagents return <= 15-20 lines.
4. Reuse a live agent within a session (e.g. `sql-drafter`) instead of spawning a new one.
5. No background learning loops; learn from failures only (lessons), batched at each job's retrospective.
6. Triangulation (two models, same question) doubles cost: opt-in per job, for numbers that drive decisions.
7. Logs are summarised by scripts (zero LLM cost); only relevant excerpts go to a model.
8. Caps checked by script: CLAUDE.md / AGENTS.md lines, one line per index entry, skill description length.
9. Keep the main session short: `/handoff` + `/clear` after each finished topic (clear-guard reminds).

## 2. The shared brain

```
agent-kit/
  skills/<name>/SKILL.md   how to do X; linked into ~/.claude/skills and ~/.codex/skills (and Gemini later)
  memory                   per project: notebooks/knowledge/{index,log}.md, lessons.md, semantic/cookbook.md
                           global: codex-harness/LESSONS.md (workflow), lessons index
  logs                     ~/agent-io-logs (all turns), .harness/commands.log, project log.md
  WHERE.md                 "where to look" table, read first by every model in any role
```

- **Skills** carry `origin: [L7, L18, P3]` in frontmatter (the lessons that shaped them; WikiSkill's PURPOSE.md,
  shortened). Each lesson that changed a skill or check ends with `Promoted to: <skill or check>`.
- **Promotion rule** (at every retrospective): a lesson seen again means its Prevent line was not enough: propose
  ONE small patch to ONE skill or check; the user approves; a rejected patch is noted in the lesson so it is not
  proposed again. No numeric validation set needed: the user is the gate.
- **Regression cases:** past failures become acceptance checks (e.g. the gate must find the 112 annotated CDT
  cells; a sketch SQL must never be shown as runnable).
- **Lessons index:** one line per lesson (id, title, Prevent), in each lessons file's header, reachable from both
  CLAUDE.md and AGENTS.md.
- Claude-only auto-memory keeps personal preferences; rules that every model must follow move to shared files.

## 3. Role-agnostic harness

- `harness new <job> --worker codex|claude` (Gemini later): an adapter per CLI (`codex exec` / `resume`,
  `claude -p` / `--resume`), same contract: task.md in -> HANDOFF.md + result.json (+ metrics.json) out,
  sandbox / worktree, no direct network.
- Orchestrator role = the `orchestrator` skill (plan with the user, write task.md + check, relay decisions,
  commit). Any model that reads it can orchestrate; the harness CLI is the same for all.
- Worktree per job (from Orca) when jobs run in parallel.
- `HARNESS_BASE` = commit pinned at `harness new`, given to every check (L17).

## 4. Data-analytics specifics

- **metrics.json**: every job states its key numbers (name -> value -> how computed -> source file).
- **Triangulate mode** (opt-in): the same task to two workers (e.g. Claude and Codex) independently; the harness
  shows both metrics.json side by side with the differences; no automatic tolerance or pass/fail: the user reviews
  the numbers and decides (Decided, user 2026-10-08).
- **Check ledger**: the review packet tabulates all `Check:` / `Claim:` lines; a `Pass: no`, or a hypothesis used as
  a conclusion, blocks accept until the user confirms.
- **Wiki hook**: an accepted job adds a `result` entry to the project `log.md`; SQL run for real goes to the cookbook.

## 5. Network and data requests (Decided, user 2026-10-08)

Workers never touch the network. They end a round with `needs_input` + `requests`; the orchestrator summarises;
the user approves; the harness fetches and stores files with a manifest (url / query, time, hash); the worker
resumes in the same session.

| level | example | approves |
|---|---|---|
| 1 read public docs | library docs, papers | orchestrator if the domain is on the user's allowlist, else user |
| 2 install a package | `uv add x` | user |
| 3 company data / paid | BigQuery, Gemini, embeddings | user, with SQL + dry run + cost; or a per-job budget |
| 4 write outside | push, email, BQ write | never a worker; orchestrator only on the user's order |

### 5.1 Access is set by the job's scope, not by the model (Decided, user 2026-10-08)

Whether a worker may use the internet (or data, or the repo) depends on what the job is, never on which model runs
it. Each task.md declares its access; presets in `agent-kit/permissions.yaml` save typing:

```yaml
# in task.md
access:
  network: none | request | direct-read     # direct-read = may search / fetch public pages itself
  data: none | snapshots | request          # company data: none, local snapshots only, or via requests
  repo: none | scope | all
  writes: [<paths>]
presets:
  web-research:  {network: direct-read, data: none, repo: none, writes: [research/]}
  data-analysis: {network: request, data: snapshots, repo: scope}
  orchestrate:   {network: request, data: request, repo: all}
```

- The same model can run a `web-research` job in the morning and a `data-analysis` job in the afternoon.
- Rule: **one job never combines `network: direct-read` with company data or credentials** (untrusted content +
  private data + a way out is the risky mix). If a task needs both, split it: a research job returns cited files, the
  orchestrator checks the sources, a data job uses them.
- Enforcement: the harness maps the job's access to the runtime of whichever model runs it (Claude: allowed
  tools; Codex: `--sandbox` / network setting; Gemini: its sandbox, verified when added) and refuses a job whose
  access cannot be enforced on that runtime.
- The user sets or changes `access` when approving task.md.

**Planning round + budget** for jobs that need data (e.g. a presentation): round 0 returns the plan and ALL data
requests; one approval; the harness pulls everything; round 1 builds. Optional per-job budget in task.md (tables +
max GB) lets the orchestrator approve level-3 requests inside it and report afterwards.

## 6. Order of work

| step | what | token cost | serves |
|---|---|---|---|
| 1 | token report script (done) + caps check | 0 | budget |
| 2 | skills into `agent-kit/skills`, linked for Claude and Codex, `origin:`; test that Codex finds and uses one | low | skills |
| 3 | lessons index + `WHERE.md` + promotion rule in the retrospective | low | learn from mistakes, where to look |
| 4 | harness `--worker claude` adapter + orchestrator skill + `HARNESS_BASE` | low | roles |
| 5 | metrics.json + check ledger in review.md | low | data quality |
| 6 | requests (4 levels) + planning round + budget | low | data access |
| 7 | triangulate mode, worktrees, status mod | medium | speed / confidence |

## 7. Decisions on the open questions (user, 2026-10-08)

1. worker-network: section 5 approved (requests in 4 levels, planning round + per-job budget); access per job scope (5.1).
2. Caps: CLAUDE.md <= 120 lines, AGENTS.md <= 120 lines, skill description <= 300 characters (checked by script).
3. Triangulation: no numeric tolerance; side-by-side numbers for the user to review.
