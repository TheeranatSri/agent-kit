"""Small deterministic reference policy, intentionally independent of gold labels."""
from __future__ import annotations

import re
from runners.base import Prediction, request_of


def words(text: str) -> set[str]:
    """Latin words and Thai spans; explicit Thai aliases handle absent spaces."""
    return set(re.findall(r"[a-z][a-z0-9_-]*|[\u0e00-\u0e7f]+", text.lower()))


class BaselineBackend:
    name = "baseline"

    def load(self) -> None:
        pass  # No parameters or external service are needed.

    def predict(self, case: dict) -> Prediction:
        state, _, request = request_of(case)
        labels = request.get("criteria", {})
        if request.get("type") != "choice" or not isinstance(labels, dict):
            return Prediction(case['case_id'], None, error="baseline supports choice mappings only")
        text = state.lower()
        task = case.get("task")
        if task == "context_retention":
            # Failures, numeric evidence, and exact paths often matter to the next step.
            keep = re.search(r"failed|failure|error|exception|ไม่ผ่าน|ล้มเหลว|ผิดพลาด|\d|(?:/|\\)[\w.-]+", text)
            label = "must_keep" if keep else "may_drop"
        elif task == "network_level":
            # Private data pulls need an orchestrator request even if web words coexist.
            if re.search(r"bigquery|data pull|fetch data|pull data|ดึงข้อมูล|ดึงตาราง|ฐานข้อมูล", text):
                label = "request"
            # Public research/search can use direct read access.
            elif re.search(r"\b(web|search|website|online|browse)\b|https?://|ค้นเว็บ|ค้นหาเว็บ|เว็บไซต์|เอกสารสาธารณะ", text):
                label = "direct-read"
            else:
                label = "none"  # No remote-source cue means local inputs suffice.
        elif task == "agent_routing":
            # Ambiguous decisions/method choices require the stronger decision route.
            if re.search(r"ambigu|method|decid|choose|trade.?off|unclear|ตัดสินใจ|เลือกวิธี|กำกวม|ไม่ชัดเจน", text):
                label = "escalate"
            # Concrete code changes are implementation work in the current scope.
            elif re.search(r"implement|fix|debug|code|test|แก้|เขียนโค้ด|ทดสอบ|ปรับโค้ด", text):
                label = "current"
            else:
                label = "cheap"  # Bounded reading/search/summary is the inexpensive default.
        elif task == "skill_selection":
            # Description overlap is transparent; Thai aliases bridge English labels.
            aliases = {
                "handoff": "ส่งต่อ เซสชัน ล้างบริบท",
                "wiki": "วิกิ บันทึกความรู้",
                "skill-creator": "สร้างสกิล ปรับสกิล ทักษะใช้ซ้ำ",
                "excel-review-workbook": "เวิร์กบุ๊ก สมุดงาน ตรวจทานตาราง",
            }
            tokens = words(text)
            scores = {}
            for key, description in labels.items():
                if key == "none":
                    continue
                english = words(key + " " + (description or ""))
                thai_hits = sum(term in text for term in aliases.get(key, "").split())
                scores[key] = len(tokens & english) + thai_hits
            # Stable mapping order breaks ties; zero overlap selects the explicit none label.
            label = max(scores, key=scores.get) if scores and max(scores.values()) else "none"
        else:
            return Prediction(case['case_id'], None, error=f"unknown task: {task}")
        if label not in labels:
            return Prediction(case['case_id'], None, error=f"rule label absent from criteria: {label}")
        return Prediction(case['case_id'], label, {key: float(key == label) for key in labels})
