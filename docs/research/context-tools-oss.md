---
type: research
status: reference
updated: 2026-10-08
sources: [web, see Sources]
by: codex gpt-6.1-sol (effort low, web search), reviewed by claude
---
# Task A — agent harness and context-management survey

Checked: **2026-10-08**. Read the requested local design, README, Orca research, and workflow lessons. No files changed.

Claim: Typesense is the best phonetic candidate; Tessl is the best agent-context candidate, but the remembered tool remains unidentified. | Status: hypothesis | Evidence: [Typesense](https://github.com/typesense/typesense), [Tessl](https://docs.tessl.io/); confirmation requires recognition by the user.

Claim: The first mechanisms to copy should be bounded tool output, selective retrieval, and small resumable handoffs. | Status: hypothesis | Evidence: [local design](/Users/theeranat.sri/agent-kit/docs/design.md), [RTK](https://github.com/rtk-ai/rtk), [Context Mode](https://github.com/mksglu/context-mode); validate with matched analytics rounds.

## Likely “type safe” candidates

| Rank | Candidate | Why it matches | What does not match |
|---|---|---|---|
| 1 | **Typesense** | Closest sound to “type safe”; free GPL search engine and paid managed cloud; retrieval infrastructure; official MCP instructions cover both agents. [Sources](https://typesense.org/docs/guide/typesense-cloud/mcp-server.html) | A search engine, not a coding-agent harness or automatic compressor. |
| 2 | **Tessl** | “Tes…” name; specifically manages coding-agent skills/context; free and paid plans; Claude Code and Codex integrations. [Docs](https://docs.tessl.io/support/supported-platforms), [plans](https://tessl.io/pricing) | **A free plan is verified; an OSS edition is not.** Documentation about OSS packages does not establish that Tessl itself is OSS. |
| 3 | **Tabby** | “Tab…” name; explicitly offers free OSS Community and paid Team/Enterprise; repository and documentation context retrieval. [Plans](https://www.tabbyml.com/pricing), [context](https://tabby.tabbyml.com/docs/administration/context/) | Primarily a self-hosted coding assistant; no direct Claude Code/Codex context adapter verified. |
| 4 | **Tapes / tapesctl** | Similar “Tap…” sound; free OSS trace capture plus paid Paper Compute platform; coding-agent sessions, search, and reusable session knowledge. [OSS](https://papercompute.com/blog/tapes-open-core/), [plans](https://papercompute.com/pricing/) | Primarily telemetry and session reuse, not automatic token reduction. |

Claim: Typesense, Tabby, and Tapes have documented free OSS offerings plus commercial offerings; Tessl has documented free/paid plans but no verified OSS core in the sources read. | Status: verified | Evidence: [Typesense](https://cloud.typesense.org/), [Tabby](https://www.tabbyml.com/pricing), [Tapes](https://papercompute.com/pricing/), [Tessl](https://tessl.io/pricing).

## Landscape: 15 tools

**Reading the table:** integration entries describe documentation, not installations tested here. “Adapter” means integration work is required. Fit ratings are **hypotheses for your setup**, assessed against a small, local, auditable harness with human review every round. “Not found” is not proof that a paid edition does not exist.

| Name | URL | License | Free OSS vs paid | Token/context mechanism | Claude Code? Codex? | Fit and reason |
|---|---|---|---|---|---|---|
| **Typesense** | [Repo](https://github.com/typesense/typesense) | GPL-3.0 | Free self-hosted engine; paid Cloud runs the same OSS engine. [Cloud](https://cloud.typesense.org/) | Keyword/vector/hybrid search enables retrieving selected knowledge instead of loading a corpus. Requires harness retrieval policy. | Both documented for **Cloud-management MCP**; that is not an automatic project-memory integration. [MCP](https://typesense.org/docs/guide/typesense-cloud/mcp-server.html) | **Med:** useful search backend, additional service to operate. |
| **Tessl** | [Docs](https://docs.tessl.io/) | Core OSS license unverified | Free service plan; paid Team/Enterprise. [Plans](https://tessl.io/pricing) | Versioned skills and dependency documentation delivered through tiles/MCP; context reuse, not general history pruning. | Both documented. [Support](https://docs.tessl.io/support/supported-platforms) | **Med:** useful context lifecycle ideas; OSS requirement unresolved. |
| **Tabby** | [Repo](https://github.com/TabbyML/tabby) | Apache-2.0 [license](https://raw.githubusercontent.com/TabbyML/tabby/main/LICENSE) | Free Community; paid Team/Enterprise. [Plans](https://www.tabbyml.com/pricing) | Indexes repository ASTs and developer docs; retrieves context for its completion/chat/search. [Mechanism](https://tabby.tabbyml.com/docs/administration/context/) | Direct adapters not verified; operates its own assistant. | **Low:** substantial assistant infrastructure beyond your harness. |
| **Tapes / tapesctl** | [Repo](https://github.com/papercomputeco/tapes) | Apache-2.0/MIT | Free capture/search/export stack; paid managed storage and intelligence. [Boundary](https://papercompute.com/blog/tapes-open-core/), [plans](https://papercompute.com/pricing/) | Stores full traces externally; search/export supports selective session reuse. No automatic savings guarantee. | Both listed by tapesctl. [Client](https://github.com/papercomputeco/tapesctl) | **Med:** useful measurement and trace retrieval; overlaps your IO logger. |
| **RTK** | [Repo](https://github.com/rtk-ai/rtk) | Apache-2.0 | Free CLI; paid edition not found in README. | Deterministic command-specific filtering, grouping, truncation, deduplication; failures retained, passing tests collapsed. | Both documented; Claude Bash hooks do not cover built-in Read/Grep/Glob. | **High:** directly addresses large logs and analytics command output. |
| **Context Mode** | [Repo](https://github.com/mksglu/context-mode) | **ELv2; source-available, not OSS** [license](https://raw.githubusercontent.com/mksglu/context-mode/main/LICENSE) | Free use within license restrictions; commercial tier not verified. | Processes raw output outside model context; indexes content/events in SQLite FTS5; retrieves relevant excerpts and restores session state. | Both documented; Codex routing has upstream/version limitations. | **High mechanism fit:** bounded output plus retrieval and continuity. |
| **Claude-Mem** | [Repo](https://github.com/thedotmack/claude-mem) | Apache-2.0 | Free core/server/adapters; hosted recall, team sync and enterprise capabilities reserved commercially. [Boundary](https://raw.githubusercontent.com/thedotmack/claude-mem/main/docs/ip-boundary.md) | Captures activity, compresses observations with AI, retrieves relevant memory across sessions. Compression itself consumes inference. | Both listed in current README. | **Med:** continuity useful; automatic capture adds cost and knowledge-review work. |
| **Context7** | [Repo](https://github.com/upstash/context7) | MIT repository | OSS MCP code; hosted Free/Pro/Enterprise plans. [Plans](https://context7.com/plans) | Retrieves current, version-specific documentation/examples; avoids loading complete documentation sets. | Both via MCP/setup tooling. | **Med:** useful for library/API questions; limited value for analytics job state. |
| **Serena** | [Repo](https://github.com/oraios/serena) | Application GPL-3.0-or-later; SolidLSP MIT. [License](https://raw.githubusercontent.com/oraios/serena/main/LICENSE) | Free LSP backend; paid JetBrains plugin. | Symbol outlines, targeted symbol bodies and references replace whole-file exploration; persistent project memory. | Both explicitly documented. | **Med:** useful for larger Python analysis repositories; less useful for tables and CSVs. |
| **LLMLingua** | [Repo](https://github.com/microsoft/LLMLingua) | MIT | Free compression code; paid edition not found. Model execution has resource costs. | Learned token selection compresses prompts/retrieved passages; configurable compression budget. | Neither turnkey; adapter/preprocessor required. | **Low initially:** exact numbers, units, negations and evidence need preservation checks. |
| **Mem0** | [Repo](https://github.com/mem0ai/mem0) | Apache-2.0 | Free library/self-hosting; managed platform includes proprietary optimizations. | Extracts persistent facts; semantic/keyword/entity retrieval returns relevant memory rather than replaying history. | CLI/API can be integrated; turnkey compatibility not verified here. | **Med:** useful retrieval ideas; extracted facts need human acceptance and provenance. |
| **Letta Code** | [Repo](https://github.com/letta-ai/letta-code) | Apache-2.0 [license](https://raw.githubusercontent.com/letta-ai/letta-code/main/LICENSE) | Local harness available; Cloud offered; paid boundary not established here. | Editable memory blocks, conversation search and git-backed MemFS; supports context rewriting and reflection. | Separate harness; uses model providers, not a verified wrapper for either CLI. | **Low:** replacement architecture and automatic learning exceed current needs. |
| **LangGraph** | [Repo](https://github.com/langchain-ai/langgraph) | MIT | Free orchestration library; commercial LangSmith/deployment services. | Durable checkpoints, explicit state, short/long-term memory and human interrupts; pruning must be implemented. | Both through custom CLI adapters, not turnkey. | **Med:** strong review/state model, but a larger implementation burden. |
| **Orca** | [Repo](https://github.com/stablyai/orca) | MIT | Free OSS desktop app; agent subscriptions remain separate; paid Orca tier not verified. | Separate agent sessions/worktrees and persistent terminal state; no context compressor verified. | Both explicitly supported. | **Med:** orchestration/review useful; parallel fan-out can add tokens. |
| **MCP Knowledge Graph Memory** | [Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | Apache-2.0 transition with retained MIT contributions. [License](https://raw.githubusercontent.com/modelcontextprotocol/servers/main/LICENSE) | Free reference server; paid edition not found. | Local entities, relations and atomic observations; `search_nodes`/`open_nodes` retrieve subsets; `read_graph` returns everything. | MCP integration expected for both; not tested here. | **Med:** simple local memory, but lacks your claim acceptance/versioning policy. |

Claim: RTK documents reductions of up to 90% in Bash output, explicitly not 90% of the bill; its token counts use a bytes/4 estimate. | Status: verified | Evidence: [RTK savings explanation in README](https://github.com/rtk-ai/rtk).

Claim: Context Mode reports a 315 KB → 5.4 KB example and documents FTS5/BM25 session retrieval; this verifies a published example, not savings in your workloads. | Status: verified | Evidence: [Context Mode README](https://github.com/mksglu/context-mode).

Claim: Mem0 explicitly says its published managed-platform benchmark scores include proprietary optimizations unavailable in the OSS SDK. | Status: verified | Evidence: [Mem0 README](https://raw.githubusercontent.com/mem0ai/mem0/main/README.md).

Claim: Checkpoints and stored memory alone do not establish token reduction; the harness must control what enters subsequent prompts. | Status: hypothesis | Evidence: [LangGraph state/memory features](https://raw.githubusercontent.com/langchain-ai/langgraph/main/README.md), [MCP full-graph versus selective retrieval tools](https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/memory/README.md); confirm by measuring injected context.

## Top 3 ideas to copy

Effort estimates assume extension of the existing file-based harness, without adopting a new framework. Savings below are **planning hypotheses**, not vendor benchmarks or additive guarantees.

| Priority | Mechanism to implement | Expected saving and denominator | Effort |
|---|---|---|---|
| **1. Bound every tool response** | Store full stdout/stderr outside context. Return exit code, counts, failures, key metrics and a path/hash. Allow explicit retrieval of a bounded excerpt. Use deterministic format-specific reducers for logs, tests, CSV and JSON. | Target **60–90% of verbose tool-result tokens**. If such results are 30% of newly admitted input, 80% reduction saves approximately **24% of that input**. | **Low–med: 2–4 days**, including exit-code, omitted-error and raw-recovery checks. |
| **2. Retrieve accepted knowledge within a budget** | Index accepted Claim/Decision/Check records with project, dataset version, date and evidence pointer. Filter scope first, then keyword/BM25 rank, deduplicate, and pack into a fixed token budget. Preserve mandatory rules separately. | Target **70–90% of repeated knowledge loading** when replacing a 10k-token dump with a 1–3k-token packet. Extraction/indexing overhead must be counted. | **Med: 3–5 days** for local indexing, invalidation and retrieval evaluation. |
| **3. Start each reviewed round from a small checkpoint** | Preserve status, accepted decisions, metric values, evidence paths, baseline commit, pending questions and next action. After human review, start fresh context from this packet; keep full transcripts outside it. Retain same-session resume as an option. | Illustrative target: replacing 40k tokens of inherited history with a 2k packet removes **95% of inherited history per subsequent call**, before reloads. Task-wide saving remains unknown. | **Low–med: 2–3 days** for schema, lifecycle and continuity checks. |

Claim: Idea 1 should be the first experiment because it extends the existing script-summary policy and can preserve raw evidence without model-generated compression. | Status: hypothesis | Evidence: [local design §1](/Users/theeranat.sri/agent-kit/docs/design.md), [RTK](https://github.com/rtk-ai/rtk); confirm on representative analytics logs.

Claim: Idea 3 targets the locally reported dominant cost: the design records 77% of one day's Claude cache reads in the main session. | Status: verified | Evidence: [design §1, recorded measurement](/Users/theeranat.sri/agent-kit/docs/design.md); underlying token-report output was not rerun here.

**Acceptance experiment:** run matched analytics tasks with and without each mechanism; record input/output/cache tokens per actor, tool-result volume, retrieval calls, elapsed time and accepted/rejected rounds. Require identical key metrics and evidence, visible failed checks, and successful continuation after handoff. Count compression, embeddings, retries and context reloads in the total.

Assumption: Preserve numerical evidence, units, denominators, source identifiers and mandatory rules verbatim; compress surrounding logs and narrative first. | Rationale: analytics review requires auditable evidence | Risk: lower compression ratio | Revisit: only after preservation tests pass.

## Sources

All checked **2026-10-08**; URLs below are primary project/vendor sources.
- Candidates: [Typesense core](https://github.com/typesense/typesense), [Cloud](https://cloud.typesense.org/), [MCP](https://typesense.org/docs/guide/typesense-cloud/mcp-server.html); [Tessl docs](https://docs.tessl.io/), [support](https://docs.tessl.io/support/supported-platforms), [plans](https://tessl.io/pricing).
- Tabby: [core](https://github.com/TabbyML/tabby), [license](https://raw.githubusercontent.com/TabbyML/tabby/main/LICENSE), [context](https://tabby.tabbyml.com/docs/administration/context/), [plans](https://www.tabbyml.com/pricing).
- Tapes: [core](https://github.com/papercomputeco/tapes), [client](https://github.com/papercomputeco/tapesctl), [open-core explanation](https://papercompute.com/blog/tapes-open-core/), [plans](https://papercompute.com/pricing/).
- Output management: [RTK](https://github.com/rtk-ai/rtk), [Context Mode](https://github.com/mksglu/context-mode), [ELv2 license](https://raw.githubusercontent.com/mksglu/context-mode/main/LICENSE).
- Memory: [Claude-Mem](https://github.com/thedotmack/claude-mem), [commercial boundary](https://raw.githubusercontent.com/thedotmack/claude-mem/main/docs/ip-boundary.md), [Mem0](https://github.com/mem0ai/mem0), [Mem0 implementation/boundary](https://raw.githubusercontent.com/mem0ai/mem0/main/README.md).
- Retrieval/compression: [Context7](https://github.com/upstash/context7), [plans](https://context7.com/plans), [Serena](https://github.com/oraios/serena), [license](https://raw.githubusercontent.com/oraios/serena/main/LICENSE), [LLMLingua](https://github.com/microsoft/LLMLingua).
- Harnesses: [Letta Code](https://github.com/letta-ai/letta-code), [license](https://raw.githubusercontent.com/letta-ai/letta-code/main/LICENSE), [LangGraph](https://github.com/langchain-ai/langgraph), [Orca](https://github.com/stablyai/orca).
- Reference memory server: [implementation/docs](https://github.com/modelcontextprotocol/servers/tree/main/src/memory), [repository licensing transition](https://raw.githubusercontent.com/modelcontextprotocol/servers/main/LICENSE).

## Open questions

Question: tool-identity | To: user | From: Codex | Which name looks familiar: Typesense, Tessl, Tabby, or Tapes? A remembered logo or feature could resolve the ambiguity.
Question: budget-objective | To: user | From: Codex | Should the harness optimize total token volume, monetary cost, or subscription quota first?
Question: continuity-policy | To: user | From: Codex | May an accepted round start a fresh worker session from a checkpoint, or must worker sessions always resume?
Question: baseline | To: orchestrator | From: Codex | Can the next experiment meter Codex tokens as well as Claude, and separate cached input from newly admitted context?