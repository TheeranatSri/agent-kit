# WikiSkill vs our skill setup

## 1. The PDF
- Title: "WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution" (p1). Authors Liyan Tang, Cyrus Rashtchian, Chun-Sung Ferng, Andrew Tomkins, Da-Cheng Juan, Tu Vu; Google Research / Virginia Tech. arXiv:2608.27454v1, dated 2026-08-28 (p1). 28 pages (pp1-14 body, 15-18 refs, 19-28 appendix incl. prompts). Preprint, not peer reviewed (unverified beyond that).
- Core idea:
  - Add a wiki layer between raw traces and skills: raw/ (immutable traces), wiki/ (patterns, index, log, skill-impact), skills/ (SKILL.md + PURPOSE.md) (p4-5).
  - A Wiki Maintainer agent turns sampled traces (max 8: 5 fail, 3 pass, each capped at 15k chars) into pattern pages with root cause and fix (p6, p21).
  - A Skill Proposer reads the wiki index and the skill-impact log and proposes one atomic skill change per iteration (p6).
  - Gate: keep a skill change only if the validation score rises; otherwise roll back the skill but never the wiki (p6).
  - Claim: the persistent wiki is what makes it work (ablation: 48.7 -> 63.7 avg on Gemini-3.5-Flash, p10-11; avg gain over best baseline +3.3 to +12.0 points, p7-8). Evolved skills also transfer across models, and sometimes beat self-evolved ones (p9-10).

## 2. Skill-management model
- Location/format: each skill is a directory with SKILL.md (frontmatter name + description, instructions, applicability) (p3); WikiSkill adds PURPOSE.md linking the skill to the wiki patterns that motivated it (p5). Proposer prompt says SKILL.md = frontmatter + When to Apply + When NOT to Apply + Instructions; PURPOSE.md = Origin + Patterns Addressed + Evolution History (p28).
- Create/update: automated. One proposal per iteration, either create or patch (append/replace/insert_after); prefer patching; "no_action" allowed; must read >=4 traces first (p6, p27-28). Wiki edits are also patch-based (p6, p26).
- Versioning/retire: the skill set is rolled back to the last accepted state on rejection (p6). skill-impact.md stores every diff, val score and accept/reject, written by the harness code, not the LLM (p5-6). No retirement or pruning of skills or wiki; the authors list wiki pruning as missing (p14).
- Finding the right skill: none tested. All active skills are injected in full into the system prompt, so triggering/retrieval is deliberately excluded (p5, p14). The wiki has index.md with one line per pattern: PROBLEM + ROOT CAUSE + FIX, "the most important part" because it decides whether an agent opens the page (p27). Related work on skill retrieval/routing is only cited (p14).
- Mistakes -> skills: failed traces -> pattern page (root cause, exact command sequence, workaround) -> skill proposal -> validation -> accept/reject logged -> next proposal reads rejections (p5-6, p12 case study: rejected "goal-directed-action", then accepted concrete rule "Never return an item to its origin").
- Evaluation: validation score on a small held-out split (10-40 tasks) must strictly improve; 3 independent runs; paired bootstrap on test, p<0.05 (p7, p20-21). Authors admit small val sets are noisy and strict gating rejects neutral edits (p14, p20).
- Multi-agent sharing: skills evolved by one model are injected into another; cross-model transfer is mostly positive but can be harmful (Qwen-4B SpreadSheet skill drops Gemini 50.5 -> 18.1, p9-10) because low-level workarounds constrain stronger models (p9). Skill discovery and execution are separate capabilities (p10). Inference agent is denied wiki access during training rollouts because access lowered results (64.8 vs 72.6 LiveMath, 60.9 vs 63.7 avg, p11).

## 3. Fit table
| Idea | Verdict | Notes |
|---|---|---|
| Separate raw / wiki / skill layers (p4) | Fits, mostly exists | We have agent-io-log + commands.log (raw), notebooks/knowledge (wiki), SKILL.md (skills). Missing: explicit rule for what graduates from lessons to skill. |
| Wiki index.md with problem+cause+fix one-liners (p27) | Fits, adapt | Our index.md is a page catalogue. Make lessons.md carry a Prevent one-liner index; one line per lesson. |
| log.md evolution log (p5) | Fits as is | We have log.md and session logs. |
| PURPOSE.md: skill -> motivating patterns (p5) | Fits, adapt | Add `origin:` lesson IDs (L7, P3) in SKILL.md frontmatter instead of a second file (keeps SKILL.md portable for Codex). |
| skill-impact.md (diff + outcome per change) (p5-6) | Adapt | git log of ~/agent-kit/skills is the diff record; add a short per-skill changelog line with the lesson that caused it. Score = human accept/reject, not a number. |
| Automated Proposer + Maintainer agents (p5-6) | Does not fit as automation | Human reviews every round; no benchmark with ground truth. Keep as human-triggered retrospective (already "every job ends with a retrospective"). |
| Validation-gated accept/rollback (p6) | Adapt | No numeric val set. Use: replay 1-3 past failure cases (from IO log) and check the Prevent line would have caught them; human approves. Git revert = rollback. |
| Wiki never rolled back, skills can be (p6) | Fits as is | Lessons stay even if the skill edit is reverted. |
| Rejected proposals logged so they are not repeated (p5, p27) | Fits | Add "tried and rejected" section to lessons/skill changelog. |
| Atomic single-skill, patch-based edits; skills short, concise (p6, p27) | Fits | Matches our short Prevent lines; avoid monolithic skills (Qwen skills ~120 lines, p11-12). |
| Full injection, no routing (p5) | Does not fit | We have SKILL.md descriptions and Claude auto-trigger; Codex has empty skills dir, so routing relies on AGENTS.md pointers. Paper gives no evidence on routing. |
| Hide wiki from agent during skill-forming rollouts (p11) | Not applicable | Concerns training on a benchmark; ours is production work. Loose analogue: do not let a retrospective rely on the same lesson text that was already injected. |
| Cross-model transfer (p9-10) | Fits with caution | Shared ~/agent-kit/skills for Claude and Codex is supported by the transfer result, but write general procedures, not model-specific workarounds; test each shared skill on both. |
| Wiki pruning (p14: missing) | We must add | lessons.md grows; need periodic merge/retire pass. |
| Benchmarks: math, web QA, spreadsheet, ALFWorld (p7, p20) | Weak evidence for us | No data-analytics tasks with BigQuery/pandas; closest is SpreadsheetBench. |

## 4. Proposals (ranked)
1. Provenance link skill <-> lesson. Add `origin: [L7, P3]` and `last_changed_because:` to frontmatter of each SKILL.md in ~/agent-kit/skills, and a `Promoted to: <skill>` line in lessons.md/LESSONS.md entries. Effort S. Beliefs: 2 (reinforce from mistakes). 
2. Lesson-to-skill promotion rule + per-job retrospective step. In codex-harness retrospective and handoff skill: if a lesson Prevent line appeared 2+ times (Seen field) or applies to a repeatable task, propose a patch to the relevant SKILL.md (atomic, one skill, append/replace) for human approval; log rejected proposals in the lesson. Files: LESSONS.md, handoff/SKILL.md, codex-harness/SKILL.md. Effort S-M. Beliefs: 1, 2.
3. Retrieval-first index of lessons: a `lessons-index.md` (or top block of lessons.md) with one line per lesson `[area] problem + cause + Prevent`, mirrored in ~/.codex/AGENTS.md and CLAUDE.md pointers (both read it first). Plus add a one-line "where to look" table (skill / lesson / cookbook / index) in agent-kit README for both agents. Effort S. Beliefs: 3 (knowing where to look), 2.
4. Replay check as the gate. Keep a `cases/` list per skill (2-3 past failures taken from the agent-io-log with Claim/Failure lines); before accepting a skill edit, a worker replays them and shows the Prevent line fires; human decides. Files: ~/agent-kit/skills/<skill>/cases.md, harness task template. Effort M. Beliefs: 1, 2.
5. Skill changelog + retire pass. `~/agent-kit/skills/CHANGELOG.md` (date, skill, change, lesson id, accepted/rejected by user) and a monthly prune of lessons and unused skills using agent-io-log usage counts. Effort M. Beliefs: 1, 3. Addresses the pruning gap the paper admits (p14).
6. Cross-model check for every shared skill: after moving to agent-kit, run each skill once under Codex and once under Claude on a small real task; keep skills procedural and model-neutral, with model-specific notes in a separate `## Claude only` / `## Codex only` section. Effort M. Beliefs: 1. Supported by p9-10 negative-transfer example.

Not recommended: building the automated Maintainer/Proposer/gating loop (needs gold-answer val sets we lack; human review already does the gate).

## 5. Unverified / cautions
- Preprint, single group (Google), self-reported; no code or data link seen in the text. Unverified: reproducibility, whether any numbers hold outside the 5 benchmarks.
- Val sets are tiny (10-40 tasks, p20) and gating uses strict ">" so accept/reject is noisy (p20); the "wiki is critical" ablation (p11) tests one model (Gemini-3.5-Flash) only. Unverified for other models.
- Table 1 baselines were rerun by the authors with matched splits; fairness of tuning for baselines is unverified (p7, p20).
- Wiki-vs-skill benefit may partly come from the proposer having a ReAct loop and more calls (1+T_ReAct, 10-20 turns per iteration, p22), a cost difference not controlled in the ablation. Hypothesis.
- No evidence on skill retrieval/routing at scale (p5, p14), on wiki pruning (p14), or on long-horizon work (p14).
- Figures such as "+15.0%" (p11) are percentage points, not relative gains (63.7 - 48.7).
- Text extracted with pypdf, not visually checked; table cells with bold/highlights lost, so which cells are bold winners (p8, p10) not verified.
