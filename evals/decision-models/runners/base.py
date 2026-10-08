"""Common contract for decision-model backends (OpenThai via Ollama, Laya via MLX, deterministic baseline).

A case is one line of local/cases.jsonl (see ../README.md and docs/research/decision-models-spec.md section 2):
{"case_id", "task", "language", "state", "questions": [{"id", "request": {"type": "choice", "instructions",
"criteria": {label: description}}, "expected": {"label"}}], "source", "rationale", "difficulty"}.
`expected` is gold data: a backend must never read it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Prediction:
    case_id: str
    label: str | None  # chosen label; None when the backend refused the case (see `error`)
    probabilities: dict[str, float] = field(default_factory=dict)  # label -> probability, as returned
    usage: dict[str, Any] = field(default_factory=dict)  # backend-reported tokens, truncation flags
    raw: dict[str, Any] = field(default_factory=dict)  # the backend's response, unchanged
    error: str | None = None  # e.g. "too_long: 1210 tokens > 1024"; never silently truncate


class Backend(Protocol):
    name: str

    def load(self) -> None:
        """Load weights / connect. Timed separately as cold load."""

    def predict(self, case: dict) -> Prediction:
        """Decide one case (exactly one question). Must not read case['questions'][0]['expected']."""


def request_of(case: dict) -> tuple[str, str, dict]:
    """(state, question_id, request) of a one-question case, without the gold label."""
    q = case["questions"][0]
    return case["state"], q["id"], dict(q["request"])
