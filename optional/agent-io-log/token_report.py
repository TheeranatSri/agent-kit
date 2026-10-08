#!/usr/bin/env python3
"""Token usage report from ~/agent-io-logs (stdlib only, no LLM calls).

    python3 token_report.py [--since YYYY-MM-DD] [--by actor|model|project|skill|day] [--top N]
    python3 token_report.py --tools [--since ...] [--top N]   tool calls (Claude and Codex): calls, errors,
        rejected, result characters (what the call added to the context), per tool and actor kind

Sums the `usage` of assistant_output and agent_report events (Claude main session and Claude subagents).
Codex events carry no usage in the log, so Codex is listed by turn count only.
Columns: turns, input, output, cache_read, cache_write (raw tokens; no prices, they change).
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os

LOGS = os.path.expanduser("~/agent-io-logs")
KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def group_key(d: dict, by: str) -> list[str]:
    if by == "actor":
        a = d.get("actor") or "?"
        return [a[:60]]
    if by == "skill":
        return [s.get("name", "?") for s in d.get("skills") or []] or ["(no skill)"]
    if by == "day":
        return [(d.get("ts") or "")[:10]]
    return [str(d.get(by) or "?")[:60]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="")
    ap.add_argument("--by", default="actor", choices=["actor", "model", "project", "skill", "day"])
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--tools", action="store_true")
    a = ap.parse_args()
    if a.tools:
        return tool_report(a)

    tot: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    codex_turns = 0
    for day in sorted(glob.glob(f"{LOGS}/????-??-??")):
        if os.path.basename(day) < a.since:
            continue
        for f in glob.glob(f"{day}/*.jsonl"):
            for line in open(f, encoding="utf-8"):
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("event") == "codex_output":
                    codex_turns += 1
                u = d.get("usage")
                if not u or d.get("event") not in ("assistant_output", "agent_report"):
                    continue
                for k in group_key(d, a.by):
                    row = tot[k]
                    row[0] += 1
                    for i, key in enumerate(KEYS, 1):
                        row[i] += int(u.get(key) or 0)

    rows = sorted(tot.items(), key=lambda kv: -(kv[1][2] + kv[1][3] + kv[1][4] + kv[1][1]))
    print(f"{a.by:<60} {'turns':>6} {'input':>10} {'output':>10} {'cache_read':>13} {'cache_write':>12}")
    for k, r in rows[: a.top]:
        print(f"{k:<60} {r[0]:>6} {r[1]:>10,} {r[2]:>10,} {r[3]:>13,} {r[4]:>12,}")
    s = [sum(r[i] for r in tot.values()) for i in range(5)]
    print(f"{'TOTAL':<60} {s[0]:>6} {s[1]:>10,} {s[2]:>10,} {s[3]:>13,} {s[4]:>12,}")
    print(f"codex turns (no usage in log): {codex_turns}")


def tool_report(a) -> None:
    rows: dict[tuple, list[int]] = collections.defaultdict(lambda: [0, 0, 0, 0])
    for day in sorted(glob.glob(f"{LOGS}/????-??-??")):
        if os.path.basename(day) < a.since:
            continue
        for f in glob.glob(f"{day}/*.jsonl"):
            for line in open(f, encoding="utf-8"):
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                actor = d.get("actor") or "?"
                kind = "codex" if actor.startswith("codex") else "agent" if actor.startswith("agent:") else actor
                for t in d.get("tools") or []:
                    r = rows[(t.get("name", "?"), kind)]
                    r[0] += 1
                    r[1] += bool(t.get("is_error"))
                    r[2] += bool(t.get("rejected"))
                    r[3] += len(str(t.get("result") or ""))
    print(f"{'tool':<28} {'actor':<8} {'calls':>6} {'errors':>6} {'rejected':>8} {'result_chars':>13}")
    for (name, kind), r in sorted(rows.items(), key=lambda kv: -kv[1][3])[: a.top]:
        print(f"{name:<28} {kind[:8]:<8} {r[0]:>6} {r[1]:>6} {r[2]:>8} {r[3]:>13,}")


if __name__ == "__main__":
    main()
