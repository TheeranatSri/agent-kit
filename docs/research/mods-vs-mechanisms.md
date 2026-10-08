---
type: research
status: reference
updated: 2026-10-08
sources: [web + local mod reference / types (Claude Code 2.1.291)]
by: codex gpt-6.1-sol (effort low, web search), reviewed by claude
---
# TASK B — Context and token reduction mechanisms

Checked **2026-10-08**. Research only; no files changed. Local mod contract examined: **Claude Code 2.1.291**.

Claim: Use mods for Claude-specific prompt composition and session interaction; keep output reduction, measurement, and job orchestration in portable scripts/harness code, attached through hooks where supported. | Status: hypothesis | Evidence: capability comparison below; confirm with a small replay pilot before installation.

## 1. Mechanism comparison

“Rewrite” means changing what reaches the model. “Own” means only tools or sessions that mechanism controls.

| Mechanism | See/rewrite tool calls | See/rewrite results; cap output | Change system prompt | Compact / clear | Spawn cheaper models | Claude / Codex |
|---|---|---|---|---|---|---|
| **Mod function hook** | Yes: `tool.call`, deny or alter inputs | Yes: return schema-valid `{result}` | Yes: `prompt.compose`, `prompt.section`; initial context through `prompt.context` | Compact API between turns; invoke/intercept commands for clear | `agent.spawn` model routing; `model.complete` for side calls | Claude; no equivalent function-hook API established for Codex |
| **Settings/lifecycle hook** | Pre-tool inspection, denial, input rewrite | Claude: `updatedToolOutput`; Codex: observe/block, replacement field not documented | Add context; no general section-editing contract | Observe pre/post compact and session lifecycle; no documented direct compact/clear method | Not a native spawning API; a script can launch a CLI | Both; contracts differ |
| **Skill** | Instruct tool use; no interception by itself | Request bounded output; no enforced cap by itself | On-demand instructions; not general prompt middleware | Handoff procedure and command guidance | Claude forked skill can select model; otherwise delegation instructions | Both; frontmatter is not fully interchangeable |
| **Subagent** | Executes its own calls | Isolates intermediate output; returns summary | Own agent instructions | Own context; does not clear parent | Configurable agent model | Both |
| **MCP** | Controls its own tool implementation | Enforce pagination, aggregation, excerpt limits at source | No general host system-prompt rewrite | No native host reset control | Only via a custom tool/backend | Both |
| **Harness CLI** | Controls launch and adapter interfaces; not all internal calls | Cap review packets/log excerpts; wrappers can bound worker output | Build task/instruction inputs; runtime-dependent overrides | Start fresh worker or resume; manage checkpoint files | Select worker model at launch | Codex now; Claude adapter proposed locally |
| **Script** | Only calls routed through it | Deterministic parsing, counts, filtering, byte caps | Edit/build instruction files when authorized | Checkpoint/check scripts; CLI adapter performs reset | Launch selected CLI/model | Both |

Claim: Claude mods can intercept tools, compose prompts, invoke compaction, and route subagents; the installed declarations are authoritative when online documentation differs. | Status: verified | Evidence: [mods reference](https://code.claude.com/docs/en/plugins/mods/reference); local `plugin-authoring/types/claude-code.d.ts`, lines 251, 2807, 8051, 12359.

Claim: Claude settings `PostToolUse` now supports `updatedToolOutput` for all tools, subject to the tool’s output shape; `additionalContext` alone adds text rather than replacing the original. | Status: verified | Evidence: [Claude hooks](https://code.claude.com/docs/en/hooks).

Claim: Codex documents lifecycle hooks with pre-tool blocking/input rewriting and post-tool observation/blocking, but its documented post-tool output contract has no replacement field; some tool paths bypass hooks. | Status: verified | Evidence: [Codex hooks](https://learn.chatgpt.com/docs/hooks).

Claim: Skills support on-demand loading; Claude `context: fork` isolates skill execution, and both products support configurable subagents. | Status: verified | Evidence: [Claude skills](https://code.claude.com/docs/en/skills), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude subagents](https://code.claude.com/docs/en/sub-agents), [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Claim: A plugin is packaging for components, not a separate context-reduction mechanism; a Claude plugin containing a function-hook module is a mod. | Status: verified | Evidence: [plugins overview](https://code.claude.com/docs/en/plugins).

## 2. Evidence from our setup

Claim: The design’s snapshot attributes 191.1M of 247.6M Claude cache-read tokens to the main session: **77.2%**. | Status: verified | Evidence: `~/agent-kit/docs/design.md`, section 1.

Claim: The live report has grown to 227.21M main-session cache reads out of 284.35M total: **79.9%**; it still does not meter Codex token usage. | Status: verified | Evidence: `python3 ~/agent-kit/optional/agent-io-log/token_report.py --since 2026-10-08 --by actor --top 3`.

Claim: Recorded main-session tool output is dominated by Bash: **656,723 characters**, versus Read **71,382**; Codex `exec` records **3,227,434** characters. | Status: verified | Evidence: same script with `--tools --top 12`.

Claim: These character counts are useful screening measurements, not exact model-input token counts or proof that a particular file dominates. | Status: verified | Evidence: `token_report.py` sums `len(str(t.get("result") or ""))` and groups by tool/actor, without filename attribution.

## 3. Ranked candidates

All savings below are **hypotheses**, not measured improvements. Ranking targets repeated main-session input first; ranges overlap and must not be added.

Assumption: Illustrative text conversion is 4 characters/token; an avoided result would otherwise remain for 20 subsequent model requests. | Rationale: makes estimates reproducible | Risk: actual tokenization, caching, and retention differ | Revisit: pilot measurements.

| Rank | Candidate / mechanism | Estimated saving and assumption | Risk / effort | Codex equivalent |
|---|---|---|---|---|
| **1** | **Bound worker/operator review packets.** Harness/script produces status, failed checks, decisions, questions, and paths; operator returns ≤20 lines. | A 100k-character log replaced by 4k removes ~24k immediate tokens and ~480k repeated input tokens under the assumption above. | Missing decisive failures. Preserve every failed Check, question, hypothesis, exit code, and evidence path. **Low–medium.** | Same harness/script; no mod needed. |
| **2** | **Reset main session after completed topics.** Extend clear-guard/wiki-note with context usage display and a handoff/clear suggestion; handoff remains a skill. | Reducing retained history from 100k to 10k tokens for 20 later requests avoids ~1.8M input tokens, less handoff/reload overhead. | Losing active constraints; premature resets. Suggest at topic boundaries, verify checkpoint before clear. **Medium.** | Interactive `/compact`, `/new`; harness starts fresh `exec` from explicit checkpoint files. |
| **3** | **Deterministic oversized-result reducer.** Shared parser plus Claude settings `PostToolUse`; mod `tool.call` only if needed for tighter integration. Cover Bash, Read, MCP, agent reports. | If 25–50% of recorded main Bash+Read characters are removable, ~45–91k immediate tokens; ~0.91–1.82M repeated input tokens at 20 later requests. | Silent loss of data/error evidence. Keep raw output, explicit omitted count, retrievable path, and schema-valid result. **Medium–high.** | Bound producer output, scripts/MCP, pre-tool rewrite. General post-result replacement not documented. |
| **4** | **Prevent full reads of known bulky artifacts.** Pre-tool hook returns a short denial directing to `harness review`, targeted excerpts, or schema inspection. | Preventing one 100k-character read avoids ~25k immediate tokens; ~500k repeated input tokens under the stated retention assumption. | Retry loops; legitimate evidence blocked; shell commands bypass filename checks. **Low–medium.** | Codex `PreToolUse` guard plus approved wrappers; sandbox for actual access boundaries. |
| **5** | **Shrink always-loaded instructions at source.** Script enforces approved caps; move procedures into skills/indexed references. | Removing 2k tokens from each of 218 main requests avoids ~436k input-token occurrences; 218 is the design snapshot, not a forecast. | Removing essential constraints; line caps miss long lines. Add byte/token estimates. **Low.** | Shared AGENTS.md/skills; Codex instruction discovery has a configurable byte limit. |
| **6** | **Route bounded search/log interpretation to a cheaper agent.** Named agent with narrow brief; optional mod `agent.spawn` policy enforces that agent’s model. | A 20k-token exploration returned as a 1k summary removes 19k from parent context; ~380k repeated parent input tokens at 20 later requests. Worker cost remains. | Extra startup/duplication, wrong routing, weak summaries. **Medium.** | Custom Codex agents or harness `--model`; verify actual model in run metadata. |
| **7** | **Trim specific prompt sections through a mod.** Inspect `prompt.compose` and `prompt.context`; remove only measured redundancy. | A stable 1k-token reduction across 218 requests removes ~218k input-token occurrences. | Behavioral regression and cache effects; system sections differ from loaded project context. **High.** | Source instruction trimming; no equivalent section middleware established. |

Claim: Rankings 1–7 and their savings are illustrative rather than demonstrated. | Status: hypothesis | Evidence: local design/report baseline above; confirm with matched tasks measuring total tokens, cache writes, retries, and unchanged review completeness.

Claim: Compaction and a fresh session are distinct options: Claude supports focused compaction, while Codex provides `/compact`, fresh-chat commands, and a configurable automatic compaction threshold. | Status: verified | Evidence: [Claude context behavior](https://code.claude.com/docs/en/how-claude-code-works), [Codex commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli), [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference).

Claim: The existing clear-guard checks handoff age when `/clear` runs; it does not currently measure context or recommend a reset. | Status: verified | Evidence: `~/tools/claude-mods/clear-guard/hooks/register.ts`.

Claim: Existing SessionStart output uses line-limited excerpts, not a global byte/token budget; wiki-note already provides deterministic note writing and a status display. | Status: verified | Evidence: `~/agent-kit/project-template/.claude/hooks/session_start_context.sh`; `~/tools/claude-mods/wiki-note/hooks/register.ts`.

Proposal: implementation-order | Options: A) bounded packets → topic reset reminders → deterministic output reducer → targeted guards → instruction caps B) prompt surgery and automatic LLM summarization first | Recommend: A | Rationale: starts with measured output and existing workflow boundaries; validate after each change.

## 4. What should stay outside mods

| Keep as | Work | Reason / recommended boundary |
|---|---|---|
| **Harness CLI** | Human review gates, rounds, session IDs, sandbox/access mapping, model/effort selection, data requests | Preserve one auditable contract across worker runtimes; mod may display status or invoke a command. |
| **Skill** | `/handoff`, orchestration procedure, wiki interpretation, retrospective judgment | Semantic work needs task context and human review; use mods for reminders and deterministic UI actions. |
| **Script** | Token reports, log parsing, caps, reconciliations, acceptance checks | Deterministic outputs can be tested and run without model calls; hooks are adapters. |
| **Settings hook** | SessionStart context and SessionEnd recovery snapshots | Existing lifecycle integration already serves the purpose; no benefit established from migrating it. |
| **MCP/source tool** | Bounded query results, pagination, data schema/sample access | Reduce output before it enters either model; do not use a mod as a data-analysis engine. |
| **Files + scripts** | Lessons/index maintenance and shared knowledge | Preserve the design’s shared brain; avoid storing essential project state only in Claude’s plugin store. |

Claim: These boundaries match the kit’s shared-file, role-agnostic design and mandatory human review loop. | Status: verified | Evidence: `~/agent-kit/docs/design.md`, sections 0–3; `~/tools/codex-harness/README.md`.

Claim: Cheaper-agent routing can lower parent-context exposure but does not inherently reduce total tokens; Codex explicitly warns that subagent workflows consume additional model/tool tokens. | Status: verified | Evidence: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Claim: A learned summary on every oversized result should be a fallback after deterministic extraction, because its own calls and errors could outweigh savings. | Status: hypothesis | Evidence: confirm using end-to-end token and retry measurements, with retained raw evidence.

Claim: MCP output limits and tool-definition deferral already exist in Claude; inspect those settings before implementing another mod-level limit. | Status: verified | Evidence: [Claude MCP](https://code.claude.com/docs/en/mcp).

## Sources

All external sources read **2026-10-08**:

- [Claude plugins](https://code.claude.com/docs/en/plugins), [mods overview](https://code.claude.com/docs/en/plugins/mods), [mods reference](https://code.claude.com/docs/en/plugins/mods/reference).
- [Claude hooks](https://code.claude.com/docs/en/hooks), [skills](https://code.claude.com/docs/en/skills), [subagents](https://code.claude.com/docs/en/sub-agents), [context/compaction](https://code.claude.com/docs/en/how-claude-code-works), [MCP](https://code.claude.com/docs/en/mcp).
- [Codex hooks](https://learn.chatgpt.com/docs/hooks), [skills](https://learn.chatgpt.com/docs/build-skills), [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli), [configuration](https://learn.chatgpt.com/docs/config-file/config-reference).
- Local: requested design §§0–3, README, Orca research, harness lessons/README, both mod implementations, template hooks, mod reference/types, and token report script/output.

## Open questions

Question: reset-threshold | To: user | From: Codex | Which topic boundaries and context threshold should trigger a reminder? Pilot 60–70% as an assumption, not an automatic clear.
Question: output-budget | To: user | From: Codex | What default result budget and evidence exceptions should apply? Candidate: 4–8k characters, with all failed checks and open questions preserved.
Question: routing-quality | To: user | From: Codex | Which cheaper agent should handle bounded searches, and which tasks must retain Opus?
Question: measurement | To: orchestrator | From: Codex | Can the pilot capture actual Codex usage, per-result sizes/paths, and rereads so savings are measured across both runtimes?