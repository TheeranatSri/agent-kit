#!/usr/bin/env python3
"""codex-harness: Claude (or you) orchestrates, Codex works, a human reviews. Any project, stdlib only.

Loop per job:  new -> run (codex exec) -> check (job's check.sh) -> awaiting_review / needs_input
               -> human feedback -> run again in the SAME Codex session (codex exec resume) -> ... -> accept.
The harness never commits and never auto-retries: every round stops for a human review.

State lives in <project>/.harness/ (added to .git/info/exclude):
  jobs/<job>/task.md        the task (written by the orchestrator)
  jobs/<job>/check.sh       acceptance check, run from the project root after each round (exit 0 = pass)
  jobs/<job>/state.json     status, codex session id, round, history
  jobs/<job>/HANDOFF.md     kept up to date by the worker, so any model can continue
  jobs/<job>/rounds/<n>/    prompt, codex log, worker result (JSON), check output, review.md

Commands (run from inside the project):
  harness init
  harness new <job> --task FILE [--check FILE | --check-cmd CMD] [--model M] [--effort E] [--scope PATH ...]
  harness run <job> [--bg]              first round (codex exec)
  harness feedback <job> (TEXT | -f FILE) [--bg]   next round in the same session (codex exec resume)
  harness review <job>                  print the review packet of the last round
  harness accept <job> | harness reject <job> [reason]
  harness status                        one line per job
  harness monitor [seconds]             live table; macOS notification when a job needs you
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

CODEX = os.environ.get("HARNESS_CODEX", "codex")  # override for tests
DEFAULT_MODEL = os.environ.get("HARNESS_MODEL", "gpt-6.1-sol")
DEFAULT_EFFORT = os.environ.get("HARNESS_EFFORT", "high")
NEEDS_HUMAN = {"awaiting_review", "needs_input", "blocked", "failed", "error"}

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["done", "needs_input", "blocked", "failed"]},
        "summary": {"type": "string"},
        "files": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": {"type": "string"}},
        "next": {"type": "string"},
    },
    "required": ["status", "summary", "files", "questions", "next"],
    "additionalProperties": False,
}

WORKER_RULES = """\
=== HARNESS RULES (you are the worker; a human reviews every round) ===
- Job: {job}. Project root: {root}. Allowed write paths: {scope}.
  Also keep {handoff} up to date. Do not write anywhere else.
- Never git commit, push or change git config. No network access is available.
- You cannot ask questions mid-run. If you need a decision you cannot take from the task, make the safest
  reasonable assumption, record it, and finish with status "needs_input" and the questions listed.
- HANDOFF: create {handoff} before any other work and update it after every finished step. Sections:
  Status (one line) / Done / Next (exact next steps in order) / Files / Decisions & assumptions /
  Open issues / How to verify (exact commands). Mark half-finished files under Next.
- The orchestrator runs the acceptance check after you finish: {check}. Run it yourself first if you can.
- Your FINAL message must be only the JSON object required by the output schema:
  status = done | needs_input | blocked | failed, summary, files (paths you changed), questions, next.
=== END HARNESS RULES ===
"""


# ---------------------------------------------------------------- helpers
def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def project_root() -> Path:
    p = Path.cwd().resolve()
    for d in (p, *p.parents):
        if (d / ".harness").is_dir() or (d / ".git").exists():
            return d
    return p


ROOT = project_root()
HDIR = ROOT / ".harness"


def jdir(job: str) -> Path:
    d = HDIR / "jobs" / job
    if not d.is_dir():
        sys.exit(f"no such job: {job} (harness new {job} ...)")
    return d


def load(job: str) -> dict:
    return json.loads((jdir(job) / "state.json").read_text(encoding="utf-8"))


def save(job: str, st: dict) -> None:
    p = jdir(job) / "state.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def notify(title: str, msg: str) -> None:
    if sys.platform == "darwin" and shutil.which("osascript"):
        safe = msg.replace('"', "'")[:200]
        subprocess.run(["osascript", "-e", f'display notification "{safe}" with title "{title}"'], check=False)


def git_changed(paths: list[str]) -> str:
    if not (ROOT / ".git").exists():
        return "(not a git repo)"
    out = subprocess.run(["git", "status", "--short", "--", *paths], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip() or "(no changes in scope)"


# ---------------------------------------------------------------- commands
def cmd_init(_a) -> None:
    (HDIR / "jobs").mkdir(parents=True, exist_ok=True)
    (HDIR / "result_schema.json").write_text(json.dumps(RESULT_SCHEMA, indent=1), encoding="utf-8")
    excl = ROOT / ".git" / "info" / "exclude"
    if excl.parent.is_dir():
        text = excl.read_text(encoding="utf-8") if excl.exists() else ""
        if ".harness/" not in text.split():
            excl.write_text(text + ("\n" if text and not text.endswith("\n") else "") + ".harness/\n", encoding="utf-8")
    print(f"initialised {HDIR}")


def cmd_new(a) -> None:
    if not HDIR.is_dir():
        cmd_init(a)
    d = HDIR / "jobs" / a.job
    if d.exists():
        sys.exit(f"job exists: {a.job}")
    d.mkdir(parents=True)
    shutil.copy(a.task, d / "task.md")
    if a.check:
        shutil.copy(a.check, d / "check.sh")
    else:
        (d / "check.sh").write_text("#!/usr/bin/env bash\nset -e\n" + (a.check_cmd or "echo 'no check defined'") + "\n")
    (d / "check.sh").chmod(0o755)
    st = {"job": a.job, "status": "created", "created": now(), "updated": now(), "model": a.model,
          "effort": a.effort, "scope": a.scope or ["."], "session_id": None, "round": 0, "pid": None,
          "max_rounds": a.max_rounds, "history": []}
    save(a.job, st)
    print(f"created job {a.job} in {d}")


def build_prompt(job: str, st: dict, body: str) -> str:
    d = jdir(job)
    rules = WORKER_RULES.format(job=job, root=ROOT, scope=", ".join(st["scope"]),
                                handoff=(d / "HANDOFF.md").relative_to(ROOT), check=(d / "check.sh").relative_to(ROOT))
    return f"{rules}\n{body}"


def start_round(job: str, body: str, resume: bool, bg: bool) -> None:
    st = load(job)
    if st["status"] == "running":
        sys.exit(f"{job} is already running (pid {st['pid']})")
    if st["status"] == "accepted":
        sys.exit(f"{job} is accepted; create a new job for more work")
    if resume and not st["session_id"]:
        sys.exit(f"{job} has no codex session yet; use: harness run {job}")
    if st["round"] >= st["max_rounds"]:
        sys.exit(f"{job} reached max_rounds={st['max_rounds']}; raise it in state.json if you really want more")
    n = st["round"] + 1
    rd = jdir(job) / "rounds" / str(n)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "prompt.md").write_text(build_prompt(job, st, body) if not resume else body, encoding="utf-8")
    st.update(status="running", round=n, updated=now())
    st["history"].append({"round": n, "kind": "resume" if resume else "start", "started": now()})
    save(job, st)
    args = [sys.executable, str(Path(__file__).resolve()), "_worker", job, str(n), "resume" if resume else "start"]
    if bg:
        p = subprocess.Popen(args, cwd=ROOT, start_new_session=True, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        st = load(job)
        st["pid"] = p.pid
        save(job, st)
        print(f"{job}: round {n} started in background (pid {p.pid}); watch with: harness monitor")
    else:
        subprocess.run(args, cwd=ROOT, check=False)
        cmd_review(argparse.Namespace(job=job))


def cmd_run(a) -> None:
    start_round(a.job, (jdir(a.job) / "task.md").read_text(encoding="utf-8"), resume=False, bg=a.bg)


def cmd_feedback(a) -> None:
    text = Path(a.file).read_text(encoding="utf-8") if a.file else a.text
    if not text:
        sys.exit("feedback text or -f FILE required")
    st = load(a.job)
    if st["status"] not in NEEDS_HUMAN | {"rejected"}:
        sys.exit(f"{a.job} is {st['status']}; feedback is for a job waiting on review")
    body = (f"=== HUMAN REVIEW FEEDBACK (round {st['round']}) ===\n{text}\n=== END FEEDBACK ===\n"
            "Apply this feedback, keep HANDOFF.md current, re-run the acceptance check, and finish with the "
            "JSON result object only.")
    start_round(a.job, body, resume=True, bg=a.bg)


def cmd_worker(a) -> None:
    """Internal: one codex round + acceptance check. Writes everything under rounds/<n>/."""
    job, n, mode = a.job, a.round, a.mode
    st = load(job)
    d = jdir(job)
    rd = d / "rounds" / str(n)
    schema = HDIR / "result_schema.json"
    if not schema.exists():
        schema.write_text(json.dumps(RESULT_SCHEMA, indent=1), encoding="utf-8")
    common = ["-m", st["model"], "-c", f'model_reasoning_effort="{st["effort"]}"',
              "--output-schema", str(schema), "-o", str(rd / "result.json")]
    if mode == "start":
        cmd = [CODEX, "exec", *common, "--color", "never", "-s", "workspace-write", "-C", str(ROOT), "-"]
    else:  # resume has no -s / -C / --color: pass the sandbox as config, cwd is the project root
        cmd = [CODEX, "exec", "resume", *common, "-c", 'sandbox_mode="workspace-write"', st["session_id"], "-"]
    t0 = time.time()
    with open(rd / "codex.log", "w", encoding="utf-8") as log, open(rd / "prompt.md", encoding="utf-8") as inp:
        rc = subprocess.run(cmd, cwd=ROOT, stdin=inp, stdout=log, stderr=subprocess.STDOUT, check=False).returncode
    logtext = (rd / "codex.log").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"session id:\s*([0-9a-fA-F-]{20,})", logtext)
    result = None
    try:
        result = json.loads((rd / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    chk = subprocess.run(["bash", str(d / "check.sh")], cwd=ROOT, capture_output=True, text=True, check=False)
    (rd / "check.txt").write_text(f"exit {chk.returncode}\n{chk.stdout}\n{chk.stderr}", encoding="utf-8")
    st = load(job)
    if m and not st["session_id"]:
        st["session_id"] = m.group(1)
    if rc != 0 or result is None:
        status = "error"
    elif result["status"] == "done":
        status = "awaiting_review"
    else:
        status = result["status"]
    h = st["history"][-1]
    h.update(ended=now(), minutes=round((time.time() - t0) / 60, 1), codex_rc=rc, check_rc=chk.returncode,
             worker_status=(result or {}).get("status"))
    st.update(status=status, pid=None, updated=now(), check_passed=chk.returncode == 0)
    save(job, st)
    write_review(job, n, result, chk.returncode, rc)
    notify("codex-harness", f"{job}: round {n} {status}, check {'pass' if chk.returncode == 0 else 'FAIL'}")


def write_review(job: str, n: int, result: dict | None, check_rc: int, codex_rc: int) -> None:
    st = load(job)
    d = jdir(job)
    rd = d / "rounds" / str(n)
    check = (rd / "check.txt").read_text(encoding="utf-8")
    handoff = (d / "HANDOFF.md").read_text(encoding="utf-8") if (d / "HANDOFF.md").exists() else "(missing)"
    r = result or {}
    lines = [
        f"# Review: {job} · round {n} · {st['status']}",
        "",
        f"- codex exit {codex_rc} · worker status **{r.get('status', '?')}** · check "
        f"**{'PASS' if check_rc == 0 else 'FAIL'}** (exit {check_rc})",
        f"- session {st['session_id']} · model {st['model']} ({st['effort']})",
        "",
        "## Worker summary",
        r.get("summary", "(no result JSON; see codex.log)"),
        "",
        "## Questions for you",
        *([f"- {q}" for q in r.get("questions", [])] or ["(none)"]),
        "",
        "## Files (worker) / changes in scope (git)",
        *[f"- {f}" for f in r.get("files", [])],
        "```",
        git_changed(st["scope"]),
        "```",
        "",
        "## Acceptance check (last 40 lines)",
        "```",
        *check.splitlines()[-40:],
        "```",
        "",
        "## Next (worker)",
        r.get("next", ""),
        "",
        "## HANDOFF.md",
        handoff,
        "",
        f"Reply: harness feedback {job} \"...\"   |   harness accept {job}   |   harness reject {job} \"reason\"",
    ]
    (rd / "review.md").write_text("\n".join(lines), encoding="utf-8")


def last_round(job: str) -> Path | None:
    rs = sorted((jdir(job) / "rounds").glob("*"), key=lambda p: int(p.name)) if (jdir(job) / "rounds").exists() else []
    return rs[-1] if rs else None


def cmd_review(a) -> None:
    rd = last_round(a.job)
    if not rd or not (rd / "review.md").exists():
        st = load(a.job)
        print(f"{a.job}: {st['status']} (no review yet)")
        return
    print((rd / "review.md").read_text(encoding="utf-8"))


def set_status(job: str, status: str, note: str = "") -> None:
    st = load(job)
    if st["status"] == "running":
        sys.exit(f"{job} is running")
    st.update(status=status, updated=now())
    st["history"].append({"round": st["round"], "kind": status, "at": now(), "note": note})
    save(job, st)
    print(f"{job}: {status}")


def cmd_accept(a) -> None:
    set_status(a.job, "accepted", "accepted by reviewer; commit is done outside the harness")


def cmd_reject(a) -> None:
    set_status(a.job, "rejected", a.reason or "")


def alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def rows() -> list[dict]:
    out = []
    for d in sorted((HDIR / "jobs").glob("*")) if (HDIR / "jobs").is_dir() else []:
        try:
            st = json.loads((d / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if st["status"] == "running" and st.get("pid") and not alive(st["pid"]):
            st["status"] = "error"  # worker died without writing its result
        hand = ""
        if (d / "HANDOFF.md").exists():
            t = (d / "HANDOFF.md").read_text(encoding="utf-8")
            m = re.search(r"^#+\s*Status\s*\n+\s*(.+)", t, re.M)
            hand = (m.group(1) if m else "").strip("*` ")
        started = st["history"][-1].get("started") if st["history"] else None
        mins = ""
        if st["status"] == "running" and started:
            mins = str(int((dt.datetime.now() - dt.datetime.fromisoformat(started)).total_seconds() // 60))
        out.append({"job": st["job"], "status": st["status"], "round": st["round"], "min": mins,
                    "check": {True: "pass", False: "FAIL"}.get(st.get("check_passed"), "-"), "handoff": hand})
    return out


def table(rs: list[dict]) -> str:
    head = f"{'JOB':22} {'STATUS':16} {'RND':>3} {'MIN':>4} {'CHECK':5}  HANDOFF STATUS"
    body = [f"{r['job'][:22]:22} {r['status']:16} {r['round']:>3} {r['min']:>4} {r['check']:5}  {r['handoff'][:70]}"
            for r in rs]
    return "\n".join([head, "-" * len(head + " " * 50), *body]) if body else "(no jobs)"


def cmd_status(_a) -> None:
    print(table(rows()))


def cmd_monitor(a) -> None:
    told: dict[str, str] = {}
    try:
        while True:
            rs = rows()
            os.system("clear")
            print(f"codex-harness · {ROOT} · {dt.datetime.now():%H:%M:%S} · refresh {a.seconds}s · Ctrl-C to quit\n")
            print(table(rs))
            wait = [r["job"] for r in rs if r["status"] in NEEDS_HUMAN]
            if wait:
                print(f"\nWaiting for you: {', '.join(wait)}   ->  harness review <job>")
            for r in rs:
                key = f"{r['status']}#{r['round']}"
                if r["status"] in NEEDS_HUMAN and told.get(r["job"]) != key:
                    notify("codex-harness", f"{r['job']} needs you: {r['status']} (round {r['round']})")
                told[r["job"]] = key
            time.sleep(a.seconds)
    except KeyboardInterrupt:
        pass


def main() -> None:
    p = argparse.ArgumentParser(prog="harness", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(f=cmd_init)
    s = sub.add_parser("new")
    s.add_argument("job")
    s.add_argument("--task", required=True)
    s.add_argument("--check")
    s.add_argument("--check-cmd")
    s.add_argument("--model", default=DEFAULT_MODEL)
    s.add_argument("--effort", default=DEFAULT_EFFORT)
    s.add_argument("--scope", nargs="*")
    s.add_argument("--max-rounds", type=int, default=5)
    s.set_defaults(f=cmd_new)
    s = sub.add_parser("run")
    s.add_argument("job")
    s.add_argument("--bg", action="store_true")
    s.set_defaults(f=cmd_run)
    s = sub.add_parser("feedback")
    s.add_argument("job")
    s.add_argument("text", nargs="?")
    s.add_argument("-f", "--file")
    s.add_argument("--bg", action="store_true")
    s.set_defaults(f=cmd_feedback)
    for name, fn in (("review", cmd_review), ("accept", cmd_accept)):
        s = sub.add_parser(name)
        s.add_argument("job")
        s.set_defaults(f=fn)
    s = sub.add_parser("reject")
    s.add_argument("job")
    s.add_argument("reason", nargs="?")
    s.set_defaults(f=cmd_reject)
    sub.add_parser("status").set_defaults(f=cmd_status)
    s = sub.add_parser("monitor")
    s.add_argument("seconds", nargs="?", type=int, default=5)
    s.set_defaults(f=cmd_monitor)
    s = sub.add_parser("_worker")
    s.add_argument("job")
    s.add_argument("round", type=int)
    s.add_argument("mode", choices=["start", "resume"])
    s.set_defaults(f=cmd_worker)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
