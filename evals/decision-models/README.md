# Local decision-model review cases

This offline test set prepares human-reviewed Thai, English and mixed-language decisions for a later comparison of OpenThai-SystemOne (Ollama), multilingual Laya (MLX) and deterministic rules. No models are downloaded or run here, and no LLM judge assigns final labels.

| Task | Proposed labels and boundary |
| --- | --- |
| context_retention | `must_keep`: evidence needed verbatim next, including failures, numbers, decisions and active paths. `may_drop`: unrelated or superseded material not needed in active context; original logs remain available. |
| agent_routing | `cheap`: bounded search/read/summary. `current`: clear implementation or investigation in approved scope. `escalate`: unresolved decisions, method choices or ambiguity requiring user/strongest-model review. |
| skill_selection | A shortlist of 3–6 real locally installed skill folder names plus `none`. Select the closest requested operation, rather than a skill merely mentioned in the text. |
| network_level | `none`: existing local inputs suffice. `request`: approved orchestrator fetch/install/data request. `direct-read`: isolated public-page research without company data or credentials. Classification never grants access; approved job scope and deterministic enforcement prevail (design §§5/5.1). |

## Files and privacy

- `build_cases.py`: stdlib-only fixed-seed candidate sampler and curated-case exporter. Contains no log excerpts.
- `local/selections.json`: locally curated scenarios, translations, source pointers, proposed labels and rationales.
- `local/cases.jsonl`: 96 common-format cases, one choice question per case.
- `local/review.csv`: UTF-8 BOM CSV for Excel; proposed labels, rationales, and blank `user_label`/`user_note` fields.
- `local/round2_changes.json`: per-case round-two audit record and label-change status; contains no copied states.

`local/` contains company material and must never be committed or shared externally. The repository already ignores `evals/*/local/`. Check both ignored status and tracked-file inventory before any later commit; an ignore pattern cannot protect files already tracked. Only this README and the generic script belong in version control.

## Sampling and adaptation

Logs are enumerated by sorted date/project path and physical line number. Nonempty user-input text or nested tool-result text forms a candidate pool, shuffled with seed `20261008`. Sampling rejects a conservative secret-pattern match and prints at most 300 characters per candidate, never entire records. This is candidate discovery, not random assignment of labels or a representative sample of all work. Human curation also uses targeted local source searches; the selections file pins the actual chosen source lines and tool indices.

The set has four tasks × three languages × eight cases. There are 32 scenario groups with parallel Thai/English/mixed adaptations, not 96 independent observations. Each rationale names the source and discloses translation/rephrasing and added decision context; added scope constraints are hypothetical evaluation conditions, not claims that the original user approved them. Proposed labels are manual judgments awaiting review.

Each cell contains four easy and four hard cases. Hard cases include misleading domain words, warnings irrelevant to the next task, superseded numbers, successful results that still contain essential evidence, and network boundaries. States contain the task and situation, without proposed verdicts, policy instructions or explanations of the label. Rationales carry the explanation. Retention states have one task line followed by `Tool output:` and a literal English excerpt from the referenced real tool result. The task line supplies Thai/mixed language content; tool evidence is never translated or annotated. All three variants share the exact same excerpt. Preserve exact active paths and numeric identifiers. The language gate requires mostly Thai for `th`, no Thai characters for `en`, and at least 15% Thai and Latin letters each for `mixed`.

Matched translations let reviewers compare language behavior, but correlate results. Any development/test split must group all languages of a scenario together using task plus numeric case suffix; report results by language and task rather than treating 96 cases as independent. Label balance is intentional coverage, not real-world frequency.

## Reproduce before human review

Run from the repository root, offline:

```bash
python3 evals/decision-models/build_cases.py sample --kind user --limit 40
python3 evals/decision-models/build_cases.py sample --kind tool --limit 40
python3 evals/decision-models/build_cases.py build
DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 .harness/drafts/decision-cases/check.py
DEVELOPER_DIR=/Library/Developer/CommandLineTools git check-ignore evals/decision-models/local/cases.jsonl evals/decision-models/local/review.csv evals/decision-models/local/selections.json
DEVELOPER_DIR=/Library/Developer/CommandLineTools git ls-files evals/decision-models/local
```

The last command must return no files. Sampling is reproducible only for an unchanged log snapshot; the pinned local selections are sufficient to reproduce exports while their source lines still exist. The exporter validates counts, language shares, lengths, skill availability, source pointers, prohibited verdict phrases, literal retention excerpts and paired scenario metadata, then regenerates JSONL and CSV without touching harness state. It refuses to overwrite a CSV containing human labels or notes; archive completed reviews locally before any deliberate regeneration.

The secret check is a narrow pattern screen, not proof that all sensitive identifiers are removed. Selected states omit credentials, internal agent IDs, Git/SSH configuration dumps and full tool records. Company content still stays local.

## Next steps

1. Open `local/review.csv` in Excel. Review every proposed label against the stated scenario and rationale, consulting the original local source when useful. Enter the final choice in `user_label` and comments in `user_note`; keep case IDs unchanged.
2. Resolve disagreements and freeze human labels. Treat the routing implementation boundary, skill-overlap cases and network installation boundary as proposals requiring review.
3. Ask separately for model downloads and local execution. Before running, verify both actual tokenizers and complete rendered requests: the 600-character state cap is only a proxy, not proof of Laya's 700-token state / 240-token question or 1,024-token sequence limits. Reject truncation rather than silently shorten evidence.
4. Send only state and request to models, never `expected`, rationale or human labels. Evaluate the human-frozen set against deterministic rules; retain originals and enforce permissions in code.
