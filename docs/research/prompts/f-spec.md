TASK F: exact input/output spec of two local decision models, so one test set can run on both.

Models (read their repos / model cards; say plainly what you could not open):
- OpenThai-SystemOne: https://github.com/iapp-technology/openthai-systemone , https://huggingface.co/iapp/OpenThai-SystemOne (v0.3; Ollama build)
- Laya: https://github.com/mizorewww/laya-mlx (runtime), multilingual checkpoint (find its exact HF id; the default
  https://huggingface.co/aac6fef/laya-typed-decisions-mlx is English), and how https://github.com/ipenywis/laya-ultrafast calls it.

Deliver (Markdown, max 150 lines):
1. Per model: install command for an Apple M1 Pro 16 GB (MPS / MLX, no CUDA), download size, RAM at load, how to call
   it from Python (code sketch, labelled "sketch, not tested"), request schema (state / context field, question
   types choice | score | noul / yes-no, option format, max options, max tokens for state + questions), response
   schema (labels, probabilities), tokenizer and how Thai text tokenizes (tokens per Thai character if documented).
2. A COMMON case format both can take: JSON fields, limits that fit BOTH (Laya's 1,024-token total context),
   how to convert a case to each model's request. Mark where the two differ and how to handle it.
3. Known limits / failure modes from their docs (e.g. OpenThai summary-relevance weakness, Laya English default).
4. What to measure for speed on the Mac (warm p50/p95, cold load, peak RAM) and how (exact timing boundaries).
