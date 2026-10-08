---
type: research
status: reference
updated: 2026-10-08
sources: [web, see Sources]
by: codex gpt-6.1-sol (effort low, web search), reviewed by claude
---
# TASK E — Cheap decision models for the harness

Checked **2026-10-08**. Read the required local design, README, Orca and TypeSafe notes. No files changed, software installed, or models tested.

Claim: OpenThai and Laya merit a local pilot; Jev is a hosted comparison option, while Clef needs substantially larger hardware. | Status: hypothesis | Evidence: [OpenThai model card](https://huggingface.co/iapp/OpenThai-SystemOne), [Laya runtime](https://github.com/mizorewww/laya-mlx), [Jev service](https://docs.typesafe.ai/models), [Clef card](https://huggingface.co/Cloudflare/clef); confirm on our machine and decisions.

## 1. Existence, ownership and dates

| Requested source | Confirmed identity, owner, licence and date |
|---|---|
| [openthai-systemone](https://github.com/iapp-technology/openthai-systemone) | Public code repository under **iApp Technology**. Independent Thai/English decision model; Apache-2.0. Model card dates initial release **2026-09-20**, v0.3 **2026-09-22**, Ollama build **2026-09-30**. [Card](https://huggingface.co/iapp/OpenThai-SystemOne) |
| [laya-ultrafast](https://github.com/ipenywis/laya-ultrafast) | Public repository maintained by **ipenywis**: port of Browser Use’s Jev browser agent to local Laya. Agent code MIT, retaining Browser Use’s 2026 copyright; underlying Laya/runtime Apache-2.0. Exact creation/latest-commit date **unconfirmed**: GitHub API and commit-history opens failed. |
| [Clef announcement](https://blog.cloudflare.com/clef-decision-models/) | Cloudflare article by Michelle Chen, Alex Reneau and Kevin Flansburg, dated **2026-10-01**. Announces Clef/Clef-flash and fine-tuning services; model releases Apache-2.0. The article itself is not an OSS package. |
| [TypeSafe Jev](https://docs.typesafe.ai/models) | TypeSafe AI’s hosted decision service; current documented model **Jev 1.13.0**. Release date not stated on the inspected models page. SDK MIT; no self-hostable weights or weight licence established in the reviewed sources. [SDK licence](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/main/LICENSE) |

## 2. Capability comparison

Numbers below are **publisher-reported**, not measurements from this run. “No inference fee” excludes hardware, electricity and integration costs.

| Name | What it is | Open weights / OSS / paid / API | Runs locally? Size, hardware | Task types | Latency / cost, with source | Thai support | Licence |
|---|---|---|---|---|---|---|---|
| **OpenThai-SystemOne** | Thai/English Qwen-based slot classifier | Open weights + code; local API; free hosted preview | **Yes:** 0.8B; CUDA, MPS or CPU. Native request limit 64k tokens. [Code](https://github.com/iapp-technology/openthai-systemone), [card](https://huggingface.co/iapp/OpenThai-SystemOne) | Choice, ordinal score, yes/no probability (`noul`); no free-text extraction documented | Three-question, 166-token ticket: **~40 ms H100; 154 ms M3 Max/MPS**. Local: no inference fee. [Card](https://huggingface.co/iapp/OpenThai-SystemOne) | Explicitly trained/evaluated for Thai; reported MASSIVE-th accuracy **90.0%**, Wisesight **51.6%**—uneven by task. [Card](https://huggingface.co/iapp/OpenThai-SystemOne) | Apache-2.0 |
| **Laya via laya-ultrafast** | Browser-agent application using a separate decision model | Agent OSS; Laya open weights; local decisions; optional hosted Jev | **Yes:** this port needs Apple Silicon, macOS 14+, Python 3.12+. Default **421M**, **1,024-token total context**. [Repository](https://github.com/ipenywis/laya-ultrafast) | Underlying model: choice, score, noul. Browser application adds rules; no arbitrary extraction. [Checkpoint](https://huggingface.co/aac6fef/laya-typed-decisions-mlx) | Application reports **~33 ms median M1 Max** per decision; no decision API fee. Planner defaults to remote OpenRouter. [Repository](https://github.com/ipenywis/laya-ultrafast) | Default checkpoint tagged English; non-English should use separate multilingual checkpoint. Thai accuracy unverified. [Checkpoint](https://huggingface.co/aac6fef/laya-typed-decisions-mlx) | Agent MIT; weights/runtime Apache-2.0 |
| **Clef** | Cloudflare multimodal decision model | Open weights + inference code; paid Workers AI API | **Yes:** 27B BF16; published custom inference tested on **single H200**. Hosted context 65,536 tokens. [Card](https://huggingface.co/Cloudflare/clef), [docs](https://developers.cloudflare.com/workers-ai/models/clef/) | Choice, score, noul; schema-bound probabilities rather than free-text extraction | Publisher benchmark **209.3 ms median / 238.6 ms p95**; hosted **$0.24/M input tokens**. [Benchmark](https://blog.cloudflare.com/clef-decision-models/), [pricing](https://developers.cloudflare.com/workers-ai/models/clef/) | No Thai-specific evaluation found in inspected sources | Apache-2.0 |
| **Clef-flash** | Smaller Cloudflare multimodal decision model | Open weights + inference code; paid API | **Yes:** 9B BF16; custom inference tested on **single H200**. Hosted context 65,536 tokens. [Card](https://huggingface.co/Cloudflare/clef-flash), [docs](https://developers.cloudflare.com/workers-ai/models/clef-flash/) | Choice, score, noul; bounded fields | Publisher benchmark **38.8 ms median / 122.4 ms p95**; hosted **$0.09/M input tokens**. [Benchmark](https://blog.cloudflare.com/clef-decision-models/), [pricing](https://developers.cloudflare.com/workers-ai/models/clef-flash/) | Thai performance unverified | Apache-2.0 |
| **Jev 1.13.0** | TypeSafe hosted text decision service | Paid API; OSS clients; local weights not established | Local SDK calls hosted service. **64k total request**, **32k state + longest question**. Size/hardware undisclosed in inspected docs. [Models](https://docs.typesafe.ai/models) | Choice, score, noul; bounded decisions, not generative extraction. [Agent guide](https://docs.typesafe.ai/introduction/coding-agents) | **$0.042/M input tokens; output free**. Cloudflare comparison reports **524.1 ms median / 536.0 ms p95**, not a TypeSafe SLA. [Pricing](https://docs.typesafe.ai/models), [comparison](https://blog.cloudflare.com/clef-decision-models/) | No Thai-specific guarantee/evaluation established here | Hosted service; Python SDK MIT |

Claim: The latency figures do not establish a fair speed ranking on our Mac: workloads, hardware and timing boundaries differ. | Status: verified | Evidence: [OpenThai timing conditions](https://huggingface.co/iapp/OpenThai-SystemOne), [Laya application measurements](https://github.com/ipenywis/laya-ultrafast), [Cloudflare benchmark](https://blog.cloudflare.com/clef-decision-models/).

Claim: OpenThai relates directly to Jev’s System One interface: it mirrors `POST /v1/systemone`, but is an independent reimplementation explicitly unaffiliated with TypeSafe AI. | Status: verified | Evidence: [repository](https://github.com/iapp-technology/openthai-systemone), [licence and credits](https://huggingface.co/iapp/OpenThai-SystemOne).

Claim: Installing laya-ultrafast unchanged does not make all processing local: its planner defaults to OpenRouter, although a local planner endpoint is supported. | Status: verified | Evidence: [configuration and planning flow](https://github.com/ipenywis/laya-ultrafast).

## 3. Fit for our decisions

The following are proposed uses, not validated deployments.

| Harness decision | Proposed fit | Boundary and comparison |
|---|---|---|
| **Keep/drop tool results** | Start with deterministic protection; pilot **OpenThai** for relevance suggestions | Include actual result evidence, current task and provenance. Preserve failed checks, accepted claims, source versions and user decisions. Laya’s short context requires small individual packets. Keep originals recoverable. |
| **Route to cheaper agent** | **Laya** for short, bounded English requests; **OpenThai** for Thai/mixed requests | Return `cheap / current / escalate`; initially review suggestions. Neither classifier establishes that the cheaper worker can complete the task correctly. |
| **Pick a skill** | Deterministic shortlist, then either local model | Send a few skill descriptions plus `none`; avoid resending the complete skill roster. Compare against shortlist-only selection to establish added value. |
| **Classify network level** | Local classifier may propose the level; deterministic policy enforces access | Model output must never grant permission or override declared scope, company-data restrictions or human approval. Ambiguous cases go to the orchestrator/user. |

Claim: OpenThai is the strongest first candidate for Thai harness decisions, but its documented weakness in summary relevance makes automatic tool-history deletion premature. | Status: hypothesis | Evidence: [Thai evaluations and summary-relevance limitation](https://huggingface.co/iapp/OpenThai-SystemOne); confirm against human-labelled retention cases.

Claim: Reuse Laya’s runtime rather than adopt the whole browser application for harness classification. | Status: hypothesis | Evidence: [browser application scope](https://github.com/ipenywis/laya-ultrafast), [standalone runtime](https://github.com/mizorewww/laya-mlx); confirm standalone inference and decision quality locally.

Claim: Clef-flash is a possible second-stage local comparator; neither Clef variant is yet justified as the default cheap Mac classifier. | Status: hypothesis | Evidence: [9B/H200 reference](https://huggingface.co/Cloudflare/clef-flash), [27B/H200 reference](https://huggingface.co/Cloudflare/clef); confirm supported runtime, memory and latency on available hardware.

Claim: Jev and hosted Clef cannot be the default path for company-data decisions under our approval rule; local OpenThai/Laya are better deployment candidates. | Status: hypothesis | Evidence: [harness access policy](/Users/theeranat.sri/agent-kit/docs/design.md), [Jev hosted endpoint](https://docs.typesafe.ai/models), [Cloudflare hosted endpoint](https://developers.cloudflare.com/workers-ai/models/clef/); verify outbound traffic is blocked in deployment.

## 4. Small local pilot: OpenThai versus Laya

**Proposed experiment; not run.** Compare OpenThai v0.3 with Laya through `laya-mlx`. Use Laya’s multilingual checkpoint for Thai/mixed cases; record the exact checkpoint rather than treating it as laya-ultrafast’s default English model.

1. **Dataset:** 120 local cases: 30 each for retention, agent routing, skill selection and network level. Include English, Thai and mixed text; include ambiguity, failed checks and embedded instructions in tool output.
2. **Labels:** user labels cases before seeing predictions. Retention: `must_keep / may_drop / uncertain`; routing: `cheap / current / escalate`; skills: fixed IDs plus `none`; network: existing levels plus `uncertain`.
3. **Inputs:** identical bounded packets containing task, relevant evidence and candidate descriptions. Fit both models’ tokenizers; report oversized cases as unsupported rather than silently truncate them. Include a deterministic-rule baseline.
4. **Split:** 40 development cases for prompt/threshold choices; freeze settings, then evaluate 80 held-out cases. Keep cases from the same job together to reduce leakage.
5. **Quality metrics:** per-task accuracy/macro-F1; must-keep false drops; network underclassification; abstention and accuracy among answered cases; label changes under reordered options.
6. **Runtime metrics:** warm p50/p95 latency, cold-load time, peak memory, input tokens and failures. Run models sequentially on the same machine; record hardware and versions.
7. **Savings test:** replay retained packets into the same reviewed continuation. Count actual orchestrator/worker input, output and cache tokens, rereads, retries and classifier overhead; check key numbers and evidence references against baseline.
8. **Human review:** one compact packet showing every disagreement/error, raw probabilities and source pointers. User decides accept/feedback/reject; **no LLM judge**, no live deletion, no automatic permission grants.

Proposal: local-decision-pilot | Options: A) OpenThai vs Laya with deterministic baseline B) Jev vs hosted Clef | Recommend: A | Rationale: tests local privacy, Thai fit and actual token savings without sending company data off-machine.

Assumption: pilot execution is a later approved round | Rationale: this task authorizes research only | Risk: hardware and runtime feasibility remain unknown | Revisit: before downloads or installation.

## 5. What this means for us

Claim: OpenThai provides a local, Apache-2.0 implementation of the Jev-style interface with explicit Thai evaluations. | Status: verified | Evidence: [model card](https://huggingface.co/iapp/OpenThai-SystemOne).
Claim: Laya offers a smaller local alternative, but its default typed-decisions checkpoint has only 1,024 tokens shared by state and questions. | Status: verified | Evidence: [checkpoint card](https://huggingface.co/aac6fef/laya-typed-decisions-mlx).
Claim: Bounded inputs, shortlists and protected evidence should precede learned pruning; cheaper decisions alone do not establish lower total token use. | Status: hypothesis | Evidence: [design §§0–3](/Users/theeranat.sri/agent-kit/docs/design.md); confirm with continuation-token measurements.
Claim: Classifiers should advise retention, routing and permissions while code and human review retain authority. | Status: hypothesis | Evidence: [local design](/Users/theeranat.sri/agent-kit/docs/design.md); validate through the proposed pilot.

## Sources

All opened sources checked **2026-10-08**; failed metadata endpoints are identified above.

- OpenThai: [repository](https://github.com/iapp-technology/openthai-systemone), [weights, evaluations, versions and licence](https://huggingface.co/iapp/OpenThai-SystemOne).
- Laya: [requested browser-agent port](https://github.com/ipenywis/laya-ultrafast), [MLX runtime](https://github.com/mizorewww/laya-mlx), [default checkpoint](https://huggingface.co/aac6fef/laya-typed-decisions-mlx), [upstream](https://github.com/NandhaKishorM/laya).
- Cloudflare: [dated announcement and benchmark](https://blog.cloudflare.com/clef-decision-models/), [Clef weights/code](https://huggingface.co/Cloudflare/clef), [Clef-flash weights/code](https://huggingface.co/Cloudflare/clef-flash), [Clef pricing](https://developers.cloudflare.com/workers-ai/models/clef/), [Clef-flash pricing](https://developers.cloudflare.com/workers-ai/models/clef-flash/).
- TypeSafe: [current models/pricing](https://docs.typesafe.ai/models), [coding-agent capabilities](https://docs.typesafe.ai/introduction/coding-agents), [SDK licence](https://raw.githubusercontent.com/typesafe-ai/typesafe-sdk-python/main/LICENSE).

## Open questions

Question: hardware | To: orchestrator | From: Codex | What chip, memory and available accelerator will host the local pilot?
Question: retention | To: user | From: Codex | Which evidence must remain verbatim in active context, versus recoverable through a local pointer?
Question: objective | To: user | From: Codex | Should selection prioritize total tokens, context occupancy, monetary cost or latency after preservation checks pass?
Question: metadata | To: researcher | From: Codex | Can a later successful GitHub metadata fetch establish laya-ultrafast’s exact creation and latest-commit dates?