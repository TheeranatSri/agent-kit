---
type: research
status: reference
updated: 2026-10-08
sources: [web, see Sources]
by: codex gpt-6.1-sol (effort low, web search), reviewed by claude
---
# TASK C — TypeSafe AI

Checked **2026-10-08**. Research only; no files changed or software installed.

Claim: TypeSafe AI is identifiable, but the useful context-management code is a community project built around its paid Jev API; I did not find a self-hostable open-source Jev edition. | Status: verified | Evidence: [official organisation](https://github.com/typesafe-ai), [model service documentation](https://docs.typesafe.ai/models), [Fast Jev Compaction](https://github.com/tamaratran/fast-jev-compaction).

Claim: For this harness, copy selective retention and context-budget monitoring first; adopting Jev pruning unchanged is premature. | Status: hypothesis | Evidence: [pruning implementation](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/compact.ts), [local design](/Users/theeranat.sri/agent-kit/docs/design.md); confirm with analytics continuation tests and total-token measurements.

## 1. Exact identity and name collisions

| Name | Website, maker and repositories | Relationship to this task |
|---|---|---|
| **TypeSafe AI / Jev** | [typesafe.ai](https://typesafe.ai/); founders Diogo Almeida, Sasha Sheng and Erik Gafni listed on its [team page](https://typesafe.ai/team). GitHub: [typesafe-ai](https://github.com/typesafe-ai). | Typed decision-model API; the confirmed company name. |
| **Fast Jev Compaction** | Community author `tamaratran`; [repository](https://github.com/tamaratran/fast-jev-compaction). | Directly relevant: Claude Code context pruning, powered by Jev. |
| **typesafe-mod** | Community author `BeLazy167`; [repository](https://github.com/BeLazy167/typesafe-mod). | Skill suggestions and advice on user-question options; optional automatic answers. |
| **TypeSafe-as-a-Judge** | Community maintainer Arik Aizikovich; [E-FL repository](https://github.com/E-FL/typesafe-as-a-judge). | MCP tools for both Claude Code and Codex; bounded semantic decisions. |
| **Typesafe at typesafe.io** | [typesafe.io](https://typesafe.io/) links to [QueryGraph](https://github.com/querygraph) and presents Rust infrastructure, semantics and typed permissions. | Another name match; its page describes a different infrastructure stack. |

Claim: Jev returns Choice, Score and Noul answers; it does not generate code, converse, or replace the model behind Claude Code or Codex. | Status: verified | Evidence: [official coding-agent explanation](https://docs.typesafe.ai/introduction/coding-agents).

Searches included `"TypeSafe AI" context tokens`, `"typesafe.ai" github`, `"typesafe" "Claude Code"`, `"Typesafe AI" "open source" context`, and `"Fast Jev Compaction" github`.

## 2. Open-source code versus paid service

Claim: The reviewed sources show separate open-source clients/integrations and a metered hosted model, rather than Community and Pro editions of one context manager. | Status: verified | Evidence: [SDK licence](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/main/LICENSE), [adapter licence](https://raw.githubusercontent.com/typesafe-ai/system-one-adapter-python/main/LICENSE), [service pricing](https://docs.typesafe.ai/models).

| Component | Licence and contents | Documented installation |
|---|---|---|
| [Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python) | MIT; synchronous/asynchronous API clients, typed questions/responses and errors. | `uv add typesafe-sdk`; set `TYPESAFE_API_KEY`. [README](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/main/README.md) |
| [JavaScript SDK](https://github.com/typesafe-ai/typesafe-sdk-js) | MIT shown by the official GitHub organisation; API client. | Package `@typesafe-ai/sdk`. [Model examples](https://docs.typesafe.ai/models) |
| [Official agent skill](https://github.com/typesafe-ai/skills) | MIT; instructions for designing Jev integrations. | Claude: marketplace `typesafe-ai/skills`, plugin `typesafe@typesafe-ai`. Codex: `npx skills add typesafe-ai/skills --skill typesafe-ai`. [README](https://raw.githubusercontent.com/typesafe-ai/skills/main/README.md) |
| [System One adapter](https://github.com/typesafe-ai/system-one-adapter-python) | MIT; substitutes ordinary provider LLMs behind the typed interface, including retry/usage diagnostics. | For this uv setup: `uv add 'system-one-adapter[anthropic]'`, or the documented OpenAI/Gemini extra. [README](https://github.com/typesafe-ai/system-one-adapter-python) |
| [Fast Jev Compaction](https://github.com/tamaratran/fast-jev-compaction) | MIT; TypeScript library plus Claude function-hook mod. | Enable `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`; set API key; marketplace `tamaratran/fast-jev-compaction`, plugin `fast-jev-compaction@fast-jev-compaction`. [Installation](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/hooks/README.md) |
| Hosted Jev | Paid inference; no model-weight licence or self-host installation found in the reviewed official sources. | API key and `POST /v1/systemone`. Current price: **$0.042/million input tokens**, output free; custom/enterprise plans offer higher limits. [Models](https://docs.typesafe.ai/models) |

Claim: Installing the free SDK or compaction mod does not supply a free local decision model. | Status: verified | Evidence: [SDK API-key requirement](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/main/README.md), [compaction transport](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/request.ts).

**Code structure inspected:** Fast Jev’s [`src/index.ts`](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/index.ts) exports `types`, `request`, `client`, `state`, `compact` and `messages`; [`hooks/fast-jev.ts`](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/hooks/fast-jev.ts) connects the library to Claude. The Python SDK exports clients under `_core/client/{sync,aio}` and the adapter exports `_client` and `_response`. [SDK entry point](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/main/src/typesafe_sdk/__init__.py), [adapter entry point](https://raw.githubusercontent.com/typesafe-ai/system-one-adapter-python/main/src/system_one_adapter/__init__.py).

## 3. Context and token mechanisms

Claim: Fast Jev performs selective deletion/truncation of tool history; retained ordinary user/assistant text stays unchanged. | Status: verified | Evidence: [implementation](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/compact.ts).

Its inspected implementation follows this sequence:

1. Pair completed calls/results by `tool_use_id`; protect pairs touching the first or newest messages. Default recent protection: **six messages**. [State code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/state.ts)
2. Construct Jev state from conversation text and tool inputs. **Result bodies are omitted**, replaced by success/error and character-count notes. Fit oversized state by progressively shortening inputs/text and omitting older state entries. [State code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/state.ts)
3. Ask two Noul questions per eligible call: retain the call? retain its complete result? Batch questions within estimated input budgets; resend the fitted state per batch. [Compaction code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/compact.ts)
4. At the default **0.5** threshold: retain both; otherwise retain call plus **300 result characters**; otherwise remove the pair. [Compaction code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/compact.ts)
5. Claude’s mod triggers compaction at **60% context usage** by default. Errors or less than **25% character reduction** delegate to built-in summary compaction. [Hook configuration](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/hooks/README.md)

Claim: The displayed reduction ratio measures characters, not actual billed-token savings; classifier calls, cache effects and rereads are outside that ratio. | Status: verified | Evidence: `messageChars`, `reductionRatio` and returned statistics in [compaction code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/compact.ts).

Claim: The classifier lacks the result-body evidence needed to distinguish important numerical output from disposable output. | Status: verified | Evidence: `resultNote` and `historyEntries` in [state code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/state.ts).

Claim: Dropping evidence while retaining assistant narration could weaken analytics review. | Status: hypothesis | Evidence: [current reconstruction code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/compact.ts); test preservation of failed checks, source versions, units and reconciliations.

Claim: Issue #65 reports fabricated completion statements after pruning; the report exists, but its proposed causal explanation was not independently reproduced here. | Status: verified | Evidence: [upstream issue](https://github.com/tamaratran/fast-jev-compaction/issues/65).

Claim: `typesafe-mod` adds a skill hint while leaving the original roster intact; it does not shrink that roster. | Status: verified | Evidence: `contextBlock` in [suggest.ts](https://raw.githubusercontent.com/BeLazy167/typesafe-mod/main/hooks/suggest.ts).

Claim: TypeSafe also documents filtering retrieved passages before generation, separating evidence/conflicts and dropping other passages; this is a cookbook pipeline, not an installed CLI-wide context manager. | Status: verified | Evidence: [RAG passage cookbook](https://docs.typesafe.ai/cookbooks/classifying_rag_passages).

## 4. Capability decisions for our setup

Claim: The following choices are implementation recommendations, with savings unverified until tested on our workloads. | Status: hypothesis | Evidence: sources below and [local mechanism comparison](/Users/theeranat.sri/agent-kit/docs/research/mods-vs-mechanisms.md).

| OSS capability | Decision | Concrete fit |
|---|---|---|
| Official integration skill | **USE AS IS**, only when implementing Jev | Documented Claude/Codex installation above; load on demand. It teaches API use, not context management. [Skill](https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md) |
| SDK typed clients | **USE AS IS**, if a Jev pilot is approved | Call from an orchestrator-owned script; return bounded results to either CLI. Preserve worker network restrictions. [SDK](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/main/README.md) |
| Provider adapter and retry accounting | **USE AS IS** for a comparison experiment | Run outside workers; compare one bounded routing question across providers, counting all attempts. [Adapter](https://github.com/typesafe-ai/system-one-adapter-python) |
| Tool-pair retention | **COPY THE IDEA** | Portable harness/script: archive raw results, retain call/result identifiers and evidence pointers; deterministically protect failed checks and accepted claims. Claude mod can apply runtime pruning; Codex uses bounded producers/checkpoints. [Code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/compact.ts) |
| Recent-history protection | **COPY THE IDEA** | Pin active task, user decisions and evidence records explicitly, alongside recency; do not rely only on message position. [Pair protection](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/state.ts) |
| Context trigger, diagnostics, fallback | **COPY THE IDEA** | Extend clear-guard with usage display/reminders; harness verifies a checkpoint before fresh Codex launch. Separate classifier failure from “nothing removable.” [Hook](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/hooks/fast-jev.ts) |
| Upstream Jev keep/drop policy unchanged | **SKIP** initially | Result bodies omitted; learned probabilities control evidence deletion; no analytics preservation evaluation. [State](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/state.ts) |
| Skill suggestion / passage selection | **COPY THE IDEA** | Index → shortlist → bounded relevant context. Start with deterministic scope/BM25; test semantic reranking only where it improves retrieval. [Skill cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion), [passage cookbook](https://docs.typesafe.ai/cookbooks/classifying_rag_passages) |
| Automatic answers to human questions | **SKIP** | Conflicts with mandatory human review each round. [Mod behaviour](https://raw.githubusercontent.com/BeLazy167/typesafe-mod/main/README.md) |
| Judge MCP routing/ranking/extraction | **COPY THE IDEA** | Closed candidate sets, explicit `no_match`, raw signals and review gates in harness scripts. Skip model judgments as acceptance authority. [MCP capabilities](https://github.com/E-FL/typesafe-as-a-judge) |

Claim: Fast Jev’s reviewed upstream adapter targets Claude function hooks; no turnkey Codex history-pruning adapter was found there. | Status: verified | Evidence: [hook code](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/hooks/fast-jev.ts), [package exports](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/src/index.ts).

## 5. Overlap, gaps and priority

Claim: Our design already plans index-first loading, short operator reports, script summaries, instruction caps and handoff/clear; earlier research proposes bounded output, accepted-knowledge retrieval and reviewed checkpoints. | Status: verified | Evidence: [design §§0–3](/Users/theeranat.sri/agent-kit/docs/design.md), [existing OSS research](/Users/theeranat.sri/agent-kit/docs/research/context-tools-oss.md).

| Comparison | Assessment |
|---|---|
| Overlap | Jev’s narrow decisions resemble cheaper-model routing; selective context resembles planned bounded retrieval. |
| Additional mechanism | Per-tool-pair retention decisions, recent-pair protection and automatic context-percentage triggers. |
| Remaining gaps | Cross-CLI enforcement, exact token metering, immutable evidence recovery, analytics-specific protection and mandatory round review. |

Claim: The comparison above favours implementing our portable output/checkpoint controls before adding an external classifier. | Status: hypothesis | Evidence: [mechanism boundaries](/Users/theeranat.sri/agent-kit/docs/research/mods-vs-mechanisms.md), [Fast Jev hook](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/hooks/fast-jev.ts); confirm through a matched pilot.

Proposal: typesafe-priority | Options: A) bounded packets → reviewed checkpoints → measured selective pruning B) install Jev pruning first | Recommend: A | Rationale: directly implements existing plans and preserves deterministic evidence controls.

**Pilot acceptance:** compare identical analytics tasks through a reviewed round and continuation. Measure both actors’ actual input/output/cache tokens, classifier overhead, rereads, retries and elapsed time. Require identical key metrics, visible failed checks, preserved decisions and recoverable source evidence.

## Sources

All external sources checked **2026-10-08**; links above identify individual supporting files.

- Official: [website](https://typesafe.ai/), [team](https://typesafe.ai/team), [GitHub organisation](https://github.com/typesafe-ai), [models/pricing](https://docs.typesafe.ai/models), [coding-agent boundary](https://docs.typesafe.ai/introduction/coding-agents).
- OSS: [Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python), [JS SDK](https://github.com/typesafe-ai/typesafe-sdk-js), [skills](https://github.com/typesafe-ai/skills), [provider adapter](https://github.com/typesafe-ai/system-one-adapter-python).
- Context: [Fast Jev repository](https://github.com/tamaratran/fast-jev-compaction), [MIT licence](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/LICENSE), [hook guide](https://raw.githubusercontent.com/tamaratran/fast-jev-compaction/main/hooks/README.md), [reported evidence-loss issue](https://github.com/tamaratran/fast-jev-compaction/issues/65).
- Other integrations: [typesafe-mod](https://github.com/BeLazy167/typesafe-mod), [judge MCP](https://github.com/E-FL/typesafe-as-a-judge), [skill-selection cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion), [passage-filtering cookbook](https://docs.typesafe.ai/cookbooks/classifying_rag_passages).
- Name distinction: [typesafe.io](https://typesafe.io/), [QueryGraph organisation](https://github.com/querygraph).

## Open questions

Question: objective | To: user | From: Codex | Which governs trade-offs first: context occupancy, total tokens, monetary cost, or subscription quota?
Question: external-classifier | To: user | From: Codex | May an orchestrator-side pilot send selected conversation text and tool inputs to TypeSafe?
Question: retention-contract | To: orchestrator | From: Codex | Which records must remain verbatim and pinned across compaction?
Question: runtime-pilot | To: orchestrator | From: Codex | Can the next pilot meter Codex usage and verify the compaction contract against installed Claude Code 2.1.291?