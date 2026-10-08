"""Lossless, offline-testable adapter for the multilingual Laya MLX runtime."""
from __future__ import annotations

import json
from typing import Any

from .base import Prediction, request_of


class LayaBackend:
    name = "laya"

    def __init__(self, model="aac6fef/laya-multilingual-mlx", dtype="float16", *, agent=None):
        self.model = model
        self.dtype = dtype
        self.agent = agent

    def load(self) -> None:
        import laya_mlx

        self.agent = laya_mlx.load(self.model, dtype=self.dtype, device="gpu", batch_size=1)

    def _preflight(self, state: str, qid: str, request: dict) -> tuple[dict, str | None]:
        """Mirror common.build_prefix's budgets, using full token spans before slicing.

        The runtime only reports state truncation; its 48-token option cap and
        crowded-option/head slicing must be checked independently.
        """
        tok = getattr(self.agent, "tok", None)
        if tok is None:
            tok = getattr(self.agent, "tokenizer", None)
        if tok is None:
            return {}, "preflight_unavailable: model tokenizer is required"
        cfg = getattr(self.agent, "cfg", {})
        max_len = min(1024, cfg.get("max_len", 1024))
        head_max = cfg.get("head_max_len", 256)
        kind = request["type"]
        ins = request["instructions"]
        if not isinstance(ins, str):
            ins = json.dumps(ins, ensure_ascii=False)
        criteria = request.get("criteria")

        def render(value: Any) -> str:
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)

        if kind == "choice":
            if isinstance(criteria, list):
                criteria = dict.fromkeys(criteria)
            options = [str(k) if v is None or v == "" else f"{k}: {render(v)}" for k, v in criteria.items()]
        elif kind == "score":
            options = [f"level {i}: {render(v)}" for i, v in enumerate(criteria)]
        elif kind == "noul":
            criteria = criteria or {}
            labels = request.get("labels", {"false": "false", "true": "true"})
            options = []
            for key, default in (("false", "no, the statement does not hold"), ("true", "yes, the statement holds")):
                value = criteria.get(key)
                options.append(labels[key].strip() + ": " + (default if value is None or value == "" else render(value)))
        else:
            return {}, f"invalid_request: unknown type {kind!r}"

        def tokens(text: str) -> list:
            return tok(text, add_special_tokens=False)["input_ids"]

        # Laya replaces literal masks with spaces. Reject that loss of input too.
        mask = tok.mask_token
        if any(mask in text for text in [state, ins, *options]):
            return {}, "too_long: special mask token collision would alter input"
        state_ids = tokens(state)
        head_ids = tokens(f"{kind} question: {ins}")
        option_ids = [tokens(" " + text) for text in options]
        usage = {"preflight": {"state_tokens": len(state_ids), "instruction_tokens": len(head_ids),
                               "option_tokens": [len(ids) for ids in option_ids]}}
        if any(tok.mask_token_id in ids for ids in [head_ids, *option_ids]):
            return usage, "too_long: option/instruction marker collision"
        if any(len(ids) > 48 for ids in option_ids):
            return usage, "too_long: option exceeds runtime's 48-token allowance"
        spans = [1 + len(ids) for ids in option_ids]
        opt_budget = head_max - sum(spans)
        if opt_budget < 16:
            per = max(4, (head_max - 16) // max(1, len(spans)))
            if any(size > per for size in spans):
                return usage, "too_long: crowded options would be shortened"
            opt_budget = head_max - sum(spans)
        if len(head_ids) > max(8, opt_budget):
            return usage, "too_long: instructions would be shortened"
        sequence = [tok.cls_token_id, *head_ids, tok.sep_token_id]
        for ids in option_ids:
            sequence.extend([tok.mask_token_id, *ids])
        sequence.extend([tok.sep_token_id, *state_ids, tok.sep_token_id])
        usage["preflight"]["prepared_tokens"] = len(sequence)
        if len(sequence) > max_len:
            return usage, f"too_long: {len(sequence)} prepared tokens > {max_len}"
        if len(state_ids) > 700 or len(sequence) - len(state_ids) - 1 > 240:
            return usage, "too_long: exceeds shared 700-state / 240-question token budget"
        if len({tuple(ids) for ids in option_ids}) != len(option_ids):
            return usage, "too_long: options have identical token spans"
        prepare = getattr(self.agent, "prepare", None)
        if prepare is not None:
            items, _ = prepare(state, {qid: request})
            item = items[0]
            usage["preflight"]["runtime_state_stats"] = dict(item.get("state_stats", {}))
            usage["preflight"]["runtime_options"] = dict(item.get("options", {}))
            if list(item["ids"]) != sequence:
                return usage, "too_long: runtime preparation altered or shortened the sequence"
        return usage, None

    def predict(self, case: dict) -> Prediction:
        case_id = case["case_id"]
        if self.agent is None:
            return Prediction(case_id, None, error="not_loaded: call load() first")
        if len(case["questions"]) != 1 or not isinstance(case["state"], str):
            return Prediction(case_id, None, error="invalid_case: require string state and one question")
        state, qid, request = request_of(case)
        usage, error = self._preflight(state, qid, request)
        if error:
            return Prediction(case_id, None, usage=usage, error=error)
        raw = self.agent.predict(state, {qid: request})
        usage.update(raw.get("usage", {}))
        if usage.get("truncated") or usage.get("state_tokens_dropped", 0) or usage.get("truncated_questions") or usage.get("options"):
            return Prediction(case_id, None, usage=usage, raw=raw, error="too_long: runtime reported truncation or collapsed options")
        answer = raw["answers"][qid]
        probabilities = dict(answer.get("probabilities", {}))
        kind = request["type"]
        if kind == "choice":
            label = answer["choice"]
            if label not in request["criteria"]:
                return Prediction(case_id, None, usage=usage, raw=raw, error="invalid_response: unknown choice label")
        elif kind == "noul":
            p = answer["noul"]
            probabilities = {"false": 1 - p, "true": p}
            label = "true" if p >= 0.5 else "false"
        else:
            # Preserve fractional score in raw; label denotes the modal level.
            label = max(probabilities, key=probabilities.get)
        return Prediction(case_id, label, probabilities=probabilities, usage=usage, raw=raw)
