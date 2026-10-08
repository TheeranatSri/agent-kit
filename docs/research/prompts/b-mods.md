TASK B: which parts of our harness should be Claude Code "mods" (plugins of function hooks) vs other mechanisms, for context / token reduction.

Read: the mod API reference at /private/tmp/claude-1539538139/bundled-skills/2.1.291/b6b93e6efc24725e4b7633f7645ec02c/plugin-authoring/reference.md (and grep the types file next to it, types/claude-code.d.ts, e.g. for 'prompt.compose', 'tool.call', 'session.compact', 'model', 'agent.spawn'); our mods in ~/tools/claude-mods (clear-guard, wiki-note); hooks in ~/agent-kit/project-template/.claude/hooks; harness ~/tools/codex-harness/README.md; token numbers in ~/agent-kit/docs/design.md section 1 (main session = 77% of cache reads); ~/agent-kit/optional/agent-io-log/token_report.py (--tools shows result characters per tool).
Use web search for official Claude Code docs on hooks, plugins, skills, subagents, compaction, and for Codex CLI equivalents (AGENTS.md, skills, hooks if any).

Deliver:
1. Table: mechanism (mod hook / settings hook / skill / subagent / MCP / harness CLI / script) x what it can do for context (see/rewrite tool calls and results, change the system prompt, trigger compact or clear, spawn cheaper models, cap tool output) x works for Claude / Codex.
2. Concrete candidates for OUR setup, ranked by expected token saving: e.g. a mod that truncates or summarises big tool results (Read of large files, codex.log), a mod that blocks reading forbidden big files, prompt.compose trimming of always-loaded sections, auto /handoff + /clear suggestion when context is large, routing searches to a cheaper subagent. For each: mechanism, what it saves (estimate, state the assumption), risk, effort, and whether Codex has an equivalent.
3. What must NOT be a mod (keep as skill / script / harness) and why.
