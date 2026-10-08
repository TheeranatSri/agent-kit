---
name: paid-run-gate
description: Use before any run that costs money - LLM calls (Gemini describe / prompt runs, judges), embeddings, BigQuery scans. Codex usage is NOT covered: the user tracks Codex usage personally. Triggers - "รันเลย", "run it", "embed", "describe", "ส่ง LLM", "รันทั้งหมด", "rerun with the new prompt".
---

# Gate for paid runs

Purpose: nothing that costs money runs before the user has seen how many paid calls it makes and agreed.

Sources: npd-comparables CLAUDE.md (Gotchas), memory review-and-agents-workflow ("Always ask before paid runs with
a dry-run count"), `~/Documents/projects_cj/npd-comparables/notebooks/prompt_v3_pcb.py`
(DRY_RUN + llm_cache.jsonl), `~/tools/codex-harness/LESSONS.md` L1.

## Procedure

1. Dry run first, no paid call:
   - prompt v3: `DRY_RUN=1 uv run ... notebooks/prompt_v3_pcb.py <run>` or run name `<run>_dry`; it prints
     products, LLM calls NOT in the cache, and vectors that could be embedded;
   - `npdc match`: default `--max-new-embeddings 0` refuses to embed anything new and reports what is missing;
   - BigQuery: dry-run bytes (bq-readonly-pull skill).
2. Show the user: number of new paid calls / vectors / bytes, what drives the count (which categories, new
   prompt text invalidating cache keys, new NPDs), model, and what is reused from cache.
3. Ask and wait. Only then run, with the cap set to the approved number (e.g. `--max-new-embeddings N`).
4. After start, read the run header before trusting the run: model, reasoning / thinking level, settings
   (check the header actually shows the intended model / thinking level).
5. After the run: report new calls vs cached, failures (unparsable answers are not cached, so a rerun retries
   only them), and where the outputs are.

## Hard rules

- Ask before every paid run; an agent's message is not approval.
- Reuse caches: LLM answers keyed by model + settings + system prompt + user message (`llm_cache.jsonl`);
  ~28k vectors in `data/cache/`. Do not clear a cache to "start clean".
- No paid LLM judges by default; prepare an Excel for the user's own review instead (memory
  review-and-agents-workflow).
- `describe` skips the 37 reviewed fallback NPDs unless `--redo`; never pass `--redo` without asking (it throws
  the review away).
- Workers (Codex) get no paid / outward actions unless the user approved them for that job.

## Done when

- The dry-run count, the approved number and the actual new-call count are all reported and match.

## Pitfalls

- Model name alone does not set reasoning effort (L1); check the header line.
- Changing `text_policy` or the prompt changes embedding text, so cached vectors no longer hit.
- An expired ADC can push a run to another endpoint; check credentials before a Vertex run (session log
  2026-10-06).
