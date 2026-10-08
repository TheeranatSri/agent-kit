---
type: research
status: reference
updated: 2026-10-08
sources: [web, see Sources]
by: codex gpt-6.1-sol (effort low, web search), reviewed by claude
---
# Task D — ideas for our harness

Checked **2026-10-08**. Read-only research; no files changed. “Verified” below means the cited source was read, not that its implementation was executed.

## Repository verification

Claim: `deepseek-ai/deepseek-harness` exists, is public, belongs to the `deepseek-ai` organization, and describes DeepSeek’s plugin-based agent harness (`dsh`). | Status: verified | Evidence: [repository metadata](https://api.github.com/repos/deepseek-ai/deepseek-harness), [README](https://github.com/deepseek-ai/deepseek-harness)

Claim: the repository uses the MIT license, copyright 2026 DeepSeek; its README labels it a rapidly changing developer preview. | Status: verified | Evidence: [LICENSE](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/LICENSE), [README](https://github.com/deepseek-ai/deepseek-harness)

**Last commit: not reliably established.** The commits API could not be opened. The returned history page showed `c291e79`, dated 2026-09-10, but was crawled three weeks earlier; repository metadata reports a later push. Do not treat that commit as current HEAD.

Claim: repository metadata reports `pushed_at: 2026-10-03T06:02:48Z`; this is a push timestamp, not proof of the latest commit’s date or hash. | Status: verified | Evidence: [metadata](https://api.github.com/repos/deepseek-ai/deepseek-harness), [returned commit history](https://github.com/deepseek-ai/deepseek-harness/commits/master/)

## 1. What it is and how it works

Claim: DSH composes its runtime from Cordis plugins; model adapters, tools, sessions and the agent loop are replaceable. Profiles combine bundles and ordered configuration patches. | Status: verified | Evidence: [architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md)

Claim: its TypeScript monorepo separates `packages/*/*`, applications, native components and website code; root scripts declare unit, coverage, end-to-end, snapshot and benchmark checks. These declarations do not establish that checks pass. | Status: verified | Evidence: [package.json](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/package.json)

Claim: an agent turn runs model requests and tool calls until no further work is owed; durable session events provide the history used to reconstruct requests. | Status: verified | Evidence: [architecture: turn flow and session log](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md)

Claim: delegation is optional and provider-based, including fresh or forked in-process children, Codex, Claude Code, ACP and DSH SDK children; continuable children and messaging are supported. | Status: verified | Evidence: [subagent documentation](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/subagent.md)

Claim: provider capabilities differ: the documented Codex and Claude Code providers reject per-call `agentOptions` overrides. A shared interface therefore does not imply identical controls across models or products. | Status: verified | Evidence: [subagent capability contract](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/subagent.md)

Claim: context compaction summarizes older balanced history while retaining recent messages, supports `/compact`, and can recover from context overflow. It costs an additional model request and cannot shrink the system prompt, tool definitions or session prefix. | Status: verified | Evidence: [compaction README](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/compaction/compaction-basic/README.md)

Claim: the compaction implementation measures the routed model’s request, optionally prunes tool results, remeasures, and summarizes only if pressure remains; missing model capacity produces an explicit configuration error. | Status: verified | Evidence: [compaction code, lines 251–321](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/compaction/compaction-basic/src/index.ts)

Claim: bounded output retention supports head, tail or head/tail previews and explicit omission metadata; truncation is kept separate from upstream incompleteness or failures. | Status: verified | Evidence: [output-retention README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/util/output-retention/README.md)

Claim: the documented sandbox vocabulary governs file effects; it explicitly does not claim network isolation, and in-process web tools remain outside that file boundary. | Status: verified | Evidence: [implemented sandbox design](https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/feature/2026-07-06-sandbox.md)

Claim: DSH’s safety notice says it has not undergone a security audit and must not be the sole security control for untrusted workloads. | Status: verified | Evidence: [SAFETY.md](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/SAFETY.md)

**Evaluation boundary:** I did not establish a shipped evaluator for analytics correctness, explanation quality or human understanding. A community proposal discusses evaluation packs and scorecards; it is proposal evidence, not proof of an implemented learning loop. [Discussion #2454](https://github.com/deepseek-ai/deepseek-harness/discussions/2454)

## 2. Ideas to borrow

Claim: our design requires one active job by default, human review every round, comparative explanations, job-specific access and role-independent Claude/Codex adapters. | Status: verified | Evidence: [design.md, sections 0–3 and 5.1](/Users/theeranat.sri/agent-kit/docs/design.md)

All implementation choices, effort estimates and expected benefits below are **hypotheses**. Effort: **S** = bounded script/CLI change; **M** = adapter or state changes with integration checks; **L** = runtime redesign.

| Idea | From | Fits our principles? | How we would build it | Effort | Take / adapt / skip and why |
|---|---|---|---|---|---|
| Bound outputs **before** they enter context; retain omission counts and recovery paths | DSH [retention](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/util/output-retention/README.md) | Yes: compact review, recoverable evidence; applies to both CLIs | Harness CLI + script: full log on disk, bounded preview, exit code and omitted-byte/item counts | S–M | **Take first.** Deterministic reduction avoids paying a model to summarize avoidable bulk. |
| Separate token measurement from compaction policy | DSH [compaction code](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/compaction/compaction-basic/src/index.ts) | Yes: model-specific capacity; no automatic new analysis round | Script + status mod: expose measured/estimated context, output reserve and budget warning | M | **Adapt.** Start with observe/warn; never report estimates as exact tokens. |
| Prune first, then compact; preserve recent work and evidence pointers | DSH [compaction](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/compaction/compaction-basic/README.md) | Conditional: summaries must retain sources, unresolved questions and method choices | Handoff skill + CLI checkpoint; use each product’s supported context controls | M | **Adapt.** Our wrapper cannot assume access to DSH’s internal history projection. |
| Durable events with a small current-state projection | DSH [architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md) | Yes: audit trail outside main context; human sees one packet | Harness CLI: record transitions, derive status/review packet by script | M | **Adapt.** Keep file-based state; avoid rebuilding the entire event runtime. |
| Declare adapter capabilities and reject unsupported requests | DSH [subagent contract](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/subagent.md) | Strong fit: access is per job, same contract for Claude/Codex | Harness CLI: adapter capability matrix and launch-time validation | M | **Take.** Permission enforcement must never silently degrade. |
| Explicit, inspectable job profiles | DSH [profiles](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md) | Yes if access stays enforced and human-approved | CLI `show-effective-config`: model, scope, access, limits, active skills | S–M | **Adapt.** Prefer static presets over dynamic plugin installation. |
| One worktree/session per job | Orca [README](https://github.com/stablyai/orca) | Yes, with concurrency defaulting to one; worktrees do not enforce network access | Harness CLI: pinned baseline and scoped worktree | M | **Adapt.** Useful isolation without fleet-sized parallelism. |
| Feedback anchored to a diff line | Orca [README](https://github.com/stablyai/orca) | Yes: small, understandable revisions across either worker | CLI feedback references: file, line, baseline; table/Claim references for analytics | S–M | **Take.** More precise than resending whole reports. |
| Explicit waits and attention notifications | Orca [orchestration discussion](https://github.com/stablyai/orca/discussions/681) | Yes: status can advance without starting another round | CLI + mod: completed, needs input, failed; separate stale-heartbeat indicator | S–M | **Adapt.** A stale heartbeat is evidence of inactivity, not proof the worker is stuck. |
| Optional dependency graph | Orca [discussion](https://github.com/stablyai/orca/discussions/681) | Conditional: one review packet and a human gate between execution rounds | CLI: dependency records; orchestrator skill explains each proposed split | M | **Defer.** Add only when real jobs need dependencies; otherwise it adds coordination overhead. |

Claim: bounded previews and script-derived status are the strongest first candidates for reducing main-session context without losing audit evidence. | Status: hypothesis | Evidence: [DSH retention](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/util/output-retention/README.md), [our token-budget design](/Users/theeranat.sri/agent-kit/docs/design.md); confirm with matched jobs measuring context growth, total tokens, rereads and review quality.

## 3. Ideas to skip or constrain

Proposal: D1 | Options: A) copy selected mechanisms into our harness B) adopt DSH as the runtime | Recommend: A | Rationale: bounded outputs and capability checks address our goal with less migration and explanation burden; this is a design judgment requiring a small pilot.

- **Skip default fan-out and “merge the winner.”** Orca advertises sending one prompt to five agents; our design permits triangulation only by choice. Hypothesis: routine fan-out increases token use and review burden. [Orca README](https://github.com/stablyai/orca), [local principles](/Users/theeranat.sri/agent-kit/docs/design.md)
- **Skip automatic review→merge→next-round chains.** They bypass our human gate. Orca discussion #681 proposes such chains; that proposal should not be represented as mandatory Orca behaviour. [Discussion](https://github.com/stablyai/orca/discussions/681), [local principles](/Users/theeranat.sri/agent-kit/docs/design.md)
- **Skip autonomous runtime/plugin evolution and LLM approval of analytics quality.** Hypothesis: changing the mechanism while it evaluates itself makes results harder for the user to explain; use deterministic regressions plus human judgment. [Evaluation proposal](https://github.com/deepseek-ai/deepseek-harness/discussions/2454), [local principles](/Users/theeranat.sri/agent-kit/docs/design.md)
- **Skip treating a file sandbox as a network policy.** Its documented boundary does not satisfy our `none/request/direct-read` contract. [Sandbox design](https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/feature/2026-07-06-sandbox.md)
- **Constrain automatic summarization.** Hypothesis: fewer visible tokens alone can conceal evidence loss or trigger costly rereads. Preserve sources and full logs; measure total cost and correctness, not just “tokens freed.” [Compaction limitations](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/compaction/compaction-basic/README.md)

## What this means for us

Claim: Orca supplies relevant workspace/review patterns; DSH supplies concrete context-retention and capability-contract patterns. | Status: verified | Evidence: [Orca](https://github.com/stablyai/orca), [DSH retention](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/util/output-retention/README.md), [subagents](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/subagent.md)
Claim: our first pilot should combine bounded tool previews, script-generated review packets and explicit adapter capabilities. | Status: hypothesis | Evidence: [design.md](/Users/theeranat.sri/agent-kit/docs/design.md); compare against the current harness on matched jobs.
Claim: compaction should follow output prevention and measurement, because it introduces its own model request and retention limits. | Status: hypothesis | Evidence: [compaction README](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/compaction/compaction-basic/README.md); confirm net savings and evidence retention.
Claim: the cited mechanisms do not establish token savings for our Claude–Codex analytics workflow. | Status: verified | Evidence: reviewed sources describe mechanisms, not a measured trial of our setup.

## Sources

All checked **2026-10-08**; returned commit-history content was stale.

- [DSH repository / README](https://github.com/deepseek-ai/deepseek-harness), [metadata](https://api.github.com/repos/deepseek-ai/deepseek-harness), [license](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/LICENSE), [commit history](https://github.com/deepseek-ai/deepseek-harness/commits/master/)
- [Architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md), [package structure and checks](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/package.json)
- [Subagents](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/subagent.md)
- [Compaction configuration](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/compaction/compaction-basic/README.md), [implementation](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/compaction/compaction-basic/src/index.ts)
- [Output retention](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/util/output-retention/README.md)
- [Sandbox design](https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/feature/2026-07-06-sandbox.md), [safety notice](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/SAFETY.md)
- [Evaluation proposal—not shipped-feature evidence](https://github.com/deepseek-ai/deepseek-harness/discussions/2454)
- [Orca README](https://github.com/stablyai/orca), [orchestration discussion](https://github.com/stablyai/orca/discussions/681)
- Local inputs: `~/tools/codex-harness/LESSONS.md`, `~/agent-kit/README.md`, `~/agent-kit/docs/design.md`, `~/agent-kit/docs/research/orca.md`.

## Open questions

- **Verification gap:** what is current DSH `master` HEAD? Obtain a fresh commit API response before implementation research.
- **Measurement gap:** which context/token metrics can each installed CLI expose reliably, including Codex usage absent from the current Claude-only report?
- **Pilot criterion:** what reduction in total tokens is acceptable only if source recovery, numerical checks and the user’s explanation of the result remain intact?