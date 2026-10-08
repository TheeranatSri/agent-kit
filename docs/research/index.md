---
type: index
status: active
updated: 2026-10-08
---
# Research notes (agent-kit)

Research knowledge: what we found out about tools and methods from outside sources. Not working knowledge (decisions,
results, plans live in each project's wiki and in `HANDOFF.md` / `design.md`). Claims marked `hypothesis` are not
verified for our setup. Prompts used for Codex runs are in `prompts/` so a run can be repeated.

- [LLM wiki (Karpathy gist)](llm-wiki.md): how a markdown wiki with index + log works as agent memory.
- [Orca](orca.md): stablyai/orca, parallel agent sessions / worktrees; comparison with our harness.
- [WikiSkill](wikiskill.md): skills that carry their purpose and origin.
- [io-log storage](io-log-storage.md): JSONL vs SQLite, measured on the real log (Decision io-log-store = B).
- [Context tools, open source](context-tools-oss.md): 15 tools that cut tokens / manage context (RTK, Context Mode,
  Claude-Mem, Typesense, Tessl, Tabby, Tapes...), free vs paid, top 3 ideas to copy.
- [Mods vs other mechanisms](mods-vs-mechanisms.md): what a Claude Code mod can do for context vs settings hooks,
  skills, subagents, MCP, harness, scripts (Claude and Codex); 7 ranked candidates for our setup.
- [TypeSafe AI](typesafe-ai.md): Jev typed decision API (paid, $0.042/M input) with MIT SDKs/skill; community
  Fast Jev Compaction mod prunes tool call/result pairs at 60% context; what to use, copy or skip for our harness.
- [Harness ideas: Orca + deepseek-harness](harness-ideas-orca-deepseek.md): what to take (bounded output before it
  enters context, adapter capability checks, inspectable job profiles, diff-anchored feedback), adapt or skip
  (default fan-out, auto merge chains, file sandbox as network policy).
- [Decision models](decision-models.md): OpenThai-SystemOne (local, Thai, Apache-2.0, Jev-compatible API), Laya
  (local, tiny, 1k context), Cloudflare Clef / Clef-flash (open weights, H200-class), TypeSafe Jev (hosted); pilot plan.
