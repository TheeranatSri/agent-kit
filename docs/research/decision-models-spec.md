---
type: research
status: reference
updated: 2026-10-08
sources: [web, see Sources]
by: codex gpt-6.1-sol (effort low, web search), reviewed by claude
---
# Task F — shared decision-model test contract
Checked **2026-10-08**. Research only: no installation, inference, or file writes.
Read local prerequisites: `~/tools/codex-harness/LESSONS.md`, `~/agent-kit/README.md`, `~/agent-kit/docs/design.md` §§0–3, and `~/agent-kit/docs/research/orca.md`.
“Verified” below means the source was read; publisher measurements were not reproduced.

## 1. Models and calls

### OpenThai-SystemOne v0.3 — Ollama build

Claim: Ollama uses a separately fine-tuned Qwen3.5 model and answer-letter probabilities, not the repository’s 256-slot head; it runs one prompt per question. | Status: verified | Evidence: [Ollama build documentation](https://ollama.com/iapp/openthai-systemone)

Installation commands, after installing the official Ollama macOS application:
```bash
ollama --version                       # require >= 0.35
ollama pull iapp/openthai-systemone:0.8b
ollama serve                          # only if the application is not serving
```
Claim: macOS 14+ and Apple M-series CPU/GPU are supported; the official installation method is the DMG application. This route needs no CUDA or Python MPS runtime. | Status: verified | Evidence: [Ollama macOS requirements](https://docs.ollama.com/macos)

Claim: The default `0.8b` download is Q8_0, listed as **812 MB**; its Modelfile sets **`num_ctx 8192`**, despite the catalogue advertising a 256K architectural window. | Status: verified | Evidence: [Ollama model listing and build description](https://ollama.com/iapp/openthai-systemone)
**RAM at load:** unknown on M1 Pro; download size is not resident memory. No applicable measured load-RAM figure was found.

Request contract:
```json
{"model":"iapp/openthai-systemone:0.8b","state":"text or JSON",
 "questions":{"q":{"type":"choice","instructions":"Question",
 "criteria":{"option_a":"description","option_b":null}}}}
```
Claim: Ollama choice questions accept **2–26 options**, with no native abstention or order-invariant mode. The entire request enters each question’s prompt. | Status: verified | Evidence: [Ollama build documentation](https://ollama.com/iapp/openthai-systemone)
Claim: The documented typed interface uses `choice` mappings, `score` lists of **2–10 ordered descriptions**, and `noul` propositions; `state` accepts text or JSON. The repository’s **64K request limit** must not be substituted for the Ollama build’s configured context. | Status: verified | Evidence: [OpenThai model card](https://huggingface.co/iapp/OpenThai-SystemOne)

Python — **sketch, not tested**; uses the common `case` defined below:
```python
import json
from urllib.request import Request, urlopen
q = case["questions"][0]
payload = {"model": "iapp/openthai-systemone:0.8b",
           "state": case["state"], "questions": {q["id"]: q["request"]}}
req = Request("http://localhost:11434/v1/systemone",
              data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
              headers={"Content-Type": "application/json"})
with urlopen(req, timeout=60) as response:
    result = json.load(response)
```
Claim: Responses contain `answers[id]`: choice → `choice`, label-keyed `probabilities`, `confidence`; score → fractional zero-based `score`, index-keyed `probabilities`, `legend`, `confidence`; noul → `noul=P(yes)`. Top-level `model` and `usage` are returned. | Status: verified | Evidence: [Ollama GGUF model card](https://huggingface.co/iapp/OpenThai-SystemOne-Ollama)

Claim: Ollama’s build uses llama.cpp tokenization of Qwen3.5 chat prompts. | Status: verified | Evidence: [OpenThai model card, Ollama changelog](https://huggingface.co/iapp/OpenThai-SystemOne)
**Thai tokens per character:** not documented in the sources read; do not assume one character equals one token.

### Laya — multilingual MLX checkpoint

Claim: The exact checkpoint is **`aac6fef/laya-multilingual-mlx`**, converted from `convaiinnovations/laya-multilingual`; it uses mmBERT-base and a **1,024-token total sequence**. | Status: verified | Evidence: [Multilingual MLX model card](https://huggingface.co/aac6fef/laya-multilingual-mlx)

Installation commands for Apple Silicon, Python 3.11+, macOS 14+:
```bash
python3 -m pip install laya-mlx huggingface_hub
hf download aac6fef/laya-multilingual-mlx
```
Claim: This runtime computes in MLX without PyTorch, Transformers inference, or CUDA. | Status: verified | Evidence: [Multilingual MLX model card](https://huggingface.co/aac6fef/laya-multilingual-mlx)

Claim: HF lists **644 MB** of model weights; tokenizer/config files add download overhead. Published FP16 weight allocation is **614.0 MiB**, and one-short-question peak MLX allocation is **687.6 MiB**, measured on M3 Max. Neither is M1 Pro process RAM at load. | Status: verified | Evidence: [HF size](https://huggingface.co/aac6fef/laya-multilingual-mlx), [memory benchmark](https://raw.githubusercontent.com/mizorewww/laya-mlx/main/BENCHMARKS.md)
**RAM at load:** unknown on M1 Pro; measure process and GPU allocation separately.

Python — **sketch, not tested**:
```python
import laya_mlx
agent = laya_mlx.load("aac6fef/laya-multilingual-mlx",
                     dtype="float16", device="gpu", batch_size=1)
q = case["questions"][0]
result = agent.predict(case["state"], {q["id"]: q["request"]})
```
Claim: `predict(state, questions)` / `system_one` accept text, JSON dictionaries, or conversation lists; questions are ID-keyed dictionaries. Choice criteria may be a mapping or unique-string list; score criteria are a nonempty list; noul is P(true). No fixed option-count cap is enforced by the inspected input validator; token budget constrains it. | Status: verified | Evidence: [MLX agent source](https://raw.githubusercontent.com/mizorewww/laya-mlx/main/laya_mlx/agent.py)

Claim: Multilingual defaults allocate **256 tokens to instructions/options** within **1,024 total**, leaving approximately 768 for state—not 1,024 state tokens. | Status: verified | Evidence: [Upstream family card](https://huggingface.co/convaiinnovations/laya)
Claim: Formatting adds special tokens; each option initially retains at most 48 text tokens, crowded options are shortened further, and instructions are also shortened. Strings/dictionaries retain the state beginning; conversation lists retain its end. | Status: verified | Evidence: [Prompt construction source](https://raw.githubusercontent.com/mizorewww/laya-mlx/main/laya_mlx/common.py)

Claim: Laya returns the same principal typed answer fields, rounded to four decimals, plus `answer_confidence` and `action.act_probability`; usage includes summed input tokens, zero output tokens, and state-truncation diagnostics. | Status: verified | Evidence: [MLX agent source](https://raw.githubusercontent.com/mizorewww/laya-mlx/main/laya_mlx/agent.py)

Claim: MLX loads the checkpoint’s `tokenizer.json` with Hugging Face’s Rust tokenizer; multilingual special tokens include `<bos>`, `<eos>`, `<mask>`, `<pad>`. | Status: verified | Evidence: [Tokenizer loader](https://raw.githubusercontent.com/mizorewww/laya-mlx/main/laya_mlx/tokenizer.py), [upstream tokenizer configuration](https://huggingface.co/convaiinnovations/laya-multilingual/blob/main/tokenizer/tokenizer_config.json)
**Thai tokens per character:** not documented in sources read; exact subword segmentation was not measured.

Claim: `laya-ultrafast` lazily loads `LAYA_MODEL`, defaults to **English `aac6fef/laya-typed-decisions-mlx`**, warms once, then calls `.system_one(state, questions)` and validates choice labels. Its `fold()` removes non-ASCII characters, so changing checkpoint alone does not make its surrounding policy Thai-ready. | Status: verified | Evidence: [ultrafast caller source](https://raw.githubusercontent.com/ipenywis/laya-ultrafast/main/laya_ultrafast/laya.py)

## 2. Common case format and adapters

**Proposed test contract**, deliberately smaller than either model’s maximum:
```json
{
  "case_id":"retain_fact_th_001",
  "language":"th",
  "task":"context_retention",
  "state":"ข้อเท็จจริงหรือสถานะงานที่ต้องประเมิน",
  "questions":[
    {"id":"retain","request":{"type":"noul",
      "instructions":"ข้อมูลนี้จำเป็นต่อการทำงานรอบถัดไปหรือไม่"},
     "expected":{"p_true":1.0}}
  ]
}
```
`expected` is human gold data; never send it to either model. `language` and `task` are evaluation metadata.

Proposed limits and validation:
- Exactly **one question per invocation**; expand multi-question cases into separate records.
- `state`: Unicode string only; identical bytes and normalization for both.
- Choice: **2–26 unique nonempty labels**; ordered mapping of label → string/null.
- Score: **2–10 nonempty strings**, ordered from lowest to highest; zero-based gold score.
- Noul: nonempty proposition instructions; omit optional criteria/custom labels for portability.
- Laya state budget: **≤700 tokens**; question/options budget: **≤240 tokens**, including option markers and rendered type/instruction prefix.
- Require actual prepared Laya sequence **≤1,024**, with **no instruction, option, or state truncation**.
- Every Laya option’s text must fit its 48-token initial allowance; reject marker/token-span collisions.
- Check the complete rendered Ollama prompt against **8,192 tokens**, using its actual tokenizer/template.
- These are tokenizer-specific limits, **not character counts**. Preflight both; reject oversize cases instead of silently trimming.

Conversion: OpenThai adds `model`, sends `state` and `{id:request}` to `/v1/systemone`; Laya passes the identical state/question dictionary directly to `predict`.
One-question calls avoid an otherwise unequal condition:
Claim: Ollama includes neighbouring questions in each prompt; Laya encodes each question with state independently. | Status: verified | Evidence: [Ollama description](https://huggingface.co/iapp/OpenThai-SystemOne-Ollama), [MLX runtime documentation](https://raw.githubusercontent.com/mizorewww/laya-mlx/main/README.md)

Normalize responses to `{case_id, question_id, type, selected_label, probabilities, expected_score, p_true, raw_usage}`.
For noul, derive `{"false":1-p_true,"true":p_true}`; for score, preserve both distribution and fractional expectation.
Do not equate `confidence` with maximum probability; compute `max(probabilities)` explicitly. Preserve raw model-specific confidence/action fields.
Use explicit `"none"` as an ordinary choice if gold cases require it; test its semantics separately.
Record input usage per backend; tokenizer differences make equal token counts inappropriate as a fairness requirement.

## 3. Limits and implications for the harness

Claim: OpenThai documents weaknesses in summary relevance, helpfulness ratings, Thai social sentiment, fine-grained English intents, and multi-step reasoning/arithmetic. | Status: verified | Evidence: [OpenThai limits](https://huggingface.co/iapp/OpenThai-SystemOne)
Its card also contains stale-looking narrative values that disagree with its tables; treat numerical performance claims as publisher reports pending reproduction.

Claim: Laya’s upstream card reports weak zero-shot typed decisions, weak ordinal scoring, overconfidence, and option-budget degradation; multilingual support does not establish quality on the harness’s retention decisions. | Status: verified | Evidence: [Laya honest limits](https://huggingface.co/convaiinnovations/laya)
Claim: These models may reduce orchestrator tokens for narrow retain/drop/escalate decisions, but suitability remains unproven. | Status: hypothesis | Evidence: `~/agent-kit/docs/design.md` §1; confirm with human-labelled Thai/English cases and end-to-end token savings.
Measure critical-fact deletion errors separately; a confident wrong deletion is more consequential than retaining unnecessary text. Keep human round review.

## 4. Mac measurement protocol — proposed, not executed

Run backends sequentially on the M1 Pro 16 GB; pin checkpoint revision/digest, runtime version, precision, context, batch size, and optimization settings.
Use identical accepted cases: Thai/English; choice/score/noul; short and near-budget inputs.
- **Cold load:** cached weights, fresh process; start immediately before `laya.load`, stop after parameters materialize/synchronize. Exclude download; report imports separately.
- **Ollama cold-to-first-answer:** unloaded runner; start before HTTP request, stop after complete JSON parsing. Includes loading and first inference; do not label it load-only.
- **First inference:** measure separately after load; preserve compilation/kernel initialization cost.
- **Warm p50/p95:** five untimed warmups, then ≥100 sequential samples per workload; start before adapter/prompt preparation, stop after synchronized inference and normalized response.
- For MLX, force completion before stopping; inspected forward code calls `mx.eval`. HTTP completion is the Ollama end boundary.
- **RAM:** baseline, post-load idle, and peak inference; sample Python RSS or the Ollama server **and runner** processes. Record sampling interval and system memory pressure/swap.
- Record MLX active/cache/peak allocations alongside RSS; do not add them as independent physical-memory totals.
- Report ms/request, ms/question, errors/truncations, and cold/warm conditions; never extrapolate M3 Max/H100 timings to M1 Pro.
Claim: Published MLX benchmarks synchronize execution, exclude loading/downloads from warm timing, and distinguish GPU allocations from other memory metrics. | Status: verified | Evidence: [Benchmark method](https://raw.githubusercontent.com/mizorewww/laya-mlx/main/BENCHMARKS.md)

## Sources

All checked 2026-10-08; links above identify the supporting passages.
- [OpenThai repository](https://github.com/iapp-technology/openthai-systemone), [main card](https://huggingface.co/iapp/OpenThai-SystemOne), [Ollama card](https://huggingface.co/iapp/OpenThai-SystemOne-Ollama), [Ollama listing](https://ollama.com/iapp/openthai-systemone).
- [Laya MLX repository](https://github.com/mizorewww/laya-mlx), [multilingual export](https://huggingface.co/aac6fef/laya-multilingual-mlx), [upstream family](https://huggingface.co/convaiinnovations/laya).
- [Ultrafast repository](https://github.com/ipenywis/laya-ultrafast); runtime, formatting, tokenizer, configuration, benchmark, and installation sources are linked inline.

## Open questions

- Cannot yet give measured M1 Pro load RAM, cold latency, warm p50/p95, or Thai token/character ratios; no model was run.
- HF export config/tokenizer detail URLs and raw OpenThai README returned tool errors; model cards opened. Upstream Laya configuration pages opened, but the export’s exact `head_max_len` still needs local confirmation.
- Before accepting the shared suite, inspect downloaded export configuration and test lossless prompt preflight; Laya’s state-truncation flag alone does not detect every instruction/option shortening.
- Which human-labelled retention cases and maximum critical-fact deletion rate define acceptance for the harness?