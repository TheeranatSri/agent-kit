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
  harness lessons <job>                 retrospective draft (what went wrong per round) -> retro.md
  harness data <job> [--done FILE... [--note T] [--bg]]   worker data requests / deliver pulled data
  harness status                        one line per job
  harness monitor [seconds]             live table; macOS notification when a job needs you
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
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
DEFAULT_EFFORT = os.environ.get("HARNESS_EFFORT", "medium")
NEEDS_HUMAN = {"awaiting_review", "needs_input", "blocked", "failed", "error"}

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["done", "needs_input", "blocked", "failed"]},
        "summary": {"type": "string"},
        "files": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": {"type": "string"}},
        "next": {"type": "string"},
        "data_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "purpose": {"type": "string"},
                    "sql": {"type": "string"},
                    "tables": {"type": "array", "items": {"type": "string"}},
                    "expected_rows": {"type": "string"},
                },
                "required": ["purpose", "sql", "tables", "expected_rows"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["status", "summary", "files", "questions", "next", "data_requests"],
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
- HANDOFF "## Status" is ONE line that you REWRITE IN PLACE every update (replace the old line; never add a
  second Status line or append a new one below). The monitor shows only that line, so it must say what is
  happening now. Done / Decisions / Open issues may grow; Next is rewritten to the current plan.
- When something goes wrong (a check fails, an assumption was wrong, you lost time), add it to HANDOFF.md under
  "## Lessons (draft)" as Problem / Cause / Fix / Prevent. The orchestrator reviews it; do not edit lessons files.
- DATA: you have no network and must never query BigQuery or any remote source. If the data you have is not
  enough, finish with status "needs_input" and put the exact read-only SQL (one SELECT / WITH statement each) in
  data_requests (purpose, sql, tables, expected_rows). Never guess data and never try network access. The
  orchestrator pulls approved requests into {datadir}/ and resumes you.
- The orchestrator runs the acceptance check after you finish: {check}. Run it yourself first if you can.
- Your FINAL message must be only the JSON object required by the output schema:
  status = done | needs_input | blocked | failed, summary, files (paths you changed), questions, next,
  data_requests ([] when none).
=== END HARNESS RULES ===
"""

AGENTS_SECTION = """\
## Lessons and multi-model work (Claude + Codex)

- **Read lessons before starting work**: the project's lessons file (`notebooks/knowledge/lessons.md` or
  `docs/lessons.md`: this project's data / domain mistakes) and `~/tools/codex-harness/LESSONS.md` (workflow:
  Claude, Codex, harness, git). Apply the `Prevent` lines.
- **Write a lesson when something goes wrong** (a failed check, a wrong claim, a silent data loss, a wasted round):
  `## P<n>. title [who: claude|codex|both] [area: ...]` with Problem / Cause (verified) / Fix / Prevent / Seen.
  Domain lessons go to the project's lessons file, workflow lessons to the harness LESSONS.md.
  If a lesson becomes a rule, enforce it where possible (a test, a check, this file).
- **Roles**: the user reviews and decides every round; the main Claude session orchestrates and commits; an Opus
  operator agent runs Codex jobs with the `harness` CLI; Codex (gpt-6.1-sol) is the worker in a sandbox, keeps
  `HANDOFF.md` current, never commits and ends with a JSON result (`needs_input` + questions when it needs a
  decision). Every job ends with a retrospective: new lessons, reviewed and committed by the orchestrator.
"""
AGENTS_HEADING = "## Lessons and multi-model work"
HARNESS_LESSONS = Path(os.environ.get("HARNESS_LESSONS", Path(__file__).resolve().parent / "LESSONS.md"))
PROJECT_LESSONS = ("notebooks/knowledge/lessons.md", "docs/lessons.md")  # first existing wins
SQL_FORBIDDEN = {"INSERT", "UPDATE", "DELETE", "MERGE", "CREATE", "DROP", "ALTER", "TRUNCATE"}
SQL_SUSPECT = {"GRANT", "REVOKE", "CALL", "EXPORT", "LOAD", "DECLARE", "SET", "EXECUTE", "EXEC", "BEGIN", "COMMIT",
               "INTO"}


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


def project_lessons_path(st: dict | None = None) -> Path | None:
    if st and st.get("lessons"):
        p = Path(st["lessons"])
        return p if p.is_absolute() else ROOT / p
    return next((ROOT / c for c in PROJECT_LESSONS if (ROOT / c).exists()), None)


def lesson_digest(path: Path | None, who: set[str]) -> list[str]:
    """Compact '- <title>: <Prevent>' lines for entries whose [who: ...] tag is in `who` (untagged = included)."""
    if not path or not path.exists():
        return []
    out = []
    text = re.sub(r"^```.*?^```", "", path.read_text(encoding="utf-8"), flags=re.M | re.S)  # skip format templates
    for block in re.split(r"^(?=## )", text, flags=re.M):
        if not block.startswith("## "):
            continue
        head = block.splitlines()[0][3:]
        m = re.search(r"\[who:\s*([a-z]+)\]", head)
        if m and m.group(1) not in who:
            continue
        if not re.search(r"^- Prevent:", block, re.M):
            continue  # intro / format sections
        title = re.sub(r"\s*\[[^]]*\]", "", head).strip()
        pm = re.search(r"^- Prevent:\s*(.*(?:\n(?![-#])\s+.*)*)", block, re.M)
        prevent = re.sub(r"\s+", " ", pm.group(1)).strip()
        out.append(f"- {title}: {prevent}")
    return out


def lessons_block(st: dict) -> str:
    who = {"codex", "both"}
    parts = []
    h = lesson_digest(HARNESS_LESSONS, who)
    if h:
        parts += [f"Workflow ({HARNESS_LESSONS}):", *h]
    pp = project_lessons_path(st)
    pl = lesson_digest(pp, who)
    if pl:
        parts += [f"Project ({pp.relative_to(ROOT) if pp.is_relative_to(ROOT) else pp}):", *pl]
    if not parts:
        return ""
    return ("=== LESSONS (mistakes made before; apply each Prevent line; full entries in the files) ===\n"
            + "\n".join(parts) + "\n=== END LESSONS ===\n")


def ensure_agents_sections() -> list[str]:
    """Append the lessons / multi-model section to CLAUDE.md (if it exists) and AGENTS.md (created if missing)."""
    done = []
    for name, create in (("CLAUDE.md", False), ("AGENTS.md", True)):
        f = ROOT / name
        if not f.exists() and not create:
            continue
        text = f.read_text(encoding="utf-8") if f.exists() else f"# {name[:-3]}\n"
        if AGENTS_HEADING in text:
            continue
        sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        f.write_text(text + sep + AGENTS_SECTION, encoding="utf-8")
        done.append(name)
    return done


# ---------------------------------------------------------------- commands
def cmd_init(_a) -> None:
    (HDIR / "jobs").mkdir(parents=True, exist_ok=True)
    (HDIR / "result_schema.json").write_text(json.dumps(RESULT_SCHEMA, indent=1), encoding="utf-8")
    excl = ROOT / ".git" / "info" / "exclude"
    if excl.parent.is_dir():
        text = excl.read_text(encoding="utf-8") if excl.exists() else ""
        if ".harness/" not in text.split():
            excl.write_text(text + ("\n" if text and not text.endswith("\n") else "") + ".harness/\n", encoding="utf-8")
    added = ensure_agents_sections()
    print(f"initialised {HDIR}" + (f"; added '{AGENTS_HEADING}' to {', '.join(added)}" if added else ""))


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
          "max_rounds": a.max_rounds, "lessons": a.lessons, "history": []}
    save(a.job, st)
    print(f"created job {a.job} in {d}")


def build_prompt(job: str, st: dict, body: str) -> str:
    d = jdir(job)
    rules = WORKER_RULES.format(job=job, root=ROOT, scope=", ".join(st["scope"]),
                                handoff=(d / "HANDOFF.md").relative_to(ROOT), check=(d / "check.sh").relative_to(ROOT),
                                datadir=(d / "data").relative_to(ROOT))
    lessons = lessons_block(st)
    return f"{rules}\n{lessons}\n{body}" if lessons else f"{rules}\n{body}"


def start_round(job: str, body: str, resume: bool, bg: bool, kind: str | None = None) -> None:
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
    st["history"].append({"round": n, "kind": kind or ("resume" if resume else "start"), "started": now()})
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
            "Apply this feedback, keep HANDOFF.md current (rewrite its one-line ## Status in place, do not append), "
            "re-run the acceptance check, and finish with the JSON result object only.")
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
    rec = {"argv": cmd, "cwd": str(ROOT), "mode": mode, "model": st["model"], "effort": st["effort"],
           "sandbox": "workspace-write", "session_id": st["session_id"], "codex_version": codex_version(),
           "stdin": str((rd / "prompt.md").relative_to(ROOT)), "prompt_sha256": sha256(rd / "prompt.md"),
           "check_sha256": sha256(d / "check.sh"), "log": str((rd / "codex.log").relative_to(ROOT)),
           "started": now(), "ended": None, "exit_code": None}
    write_json(rd / "command.json", rec)
    with open(rd / "codex.log", "w", encoding="utf-8") as log, open(rd / "prompt.md", encoding="utf-8") as inp:
        rc = subprocess.run(cmd, cwd=ROOT, stdin=inp, stdout=log, stderr=subprocess.STDOUT, check=False).returncode
    rec.update(ended=now(), exit_code=rc, duration_s=round(time.time() - t0, 1))
    logtext = (rd / "codex.log").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"session id:\s*([0-9a-fA-F-]{20,})", logtext)
    result = None
    try:
        result = json.loads((rd / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    chk_argv = ["bash", str(d / "check.sh")]
    chk_src = (d / "check.sh").read_text(encoding="utf-8", errors="replace")
    c0, c_started = time.time(), now()
    chk = subprocess.run(chk_argv, cwd=ROOT, capture_output=True, text=True, check=False)
    (rd / "check.txt").write_text(f"exit {chk.returncode}\n{chk.stdout}\n{chk.stderr}", encoding="utf-8")
    write_json(rd / "check_command.json", {"argv": chk_argv, "cwd": str(ROOT), "check_sh": chk_src,
                                           "check_sha256": sha256(d / "check.sh"), "started": c_started,
                                           "ended": now(), "duration_s": round(time.time() - c0, 1),
                                           "exit_code": chk.returncode, "stdout": chk.stdout, "stderr": chk.stderr})
    st = load(job)
    if m and not st["session_id"]:
        st["session_id"] = m.group(1)
    rec["session_id"] = st["session_id"]
    write_json(rd / "command.json", rec)
    if rc != 0 or result is None:
        status = "error"
    elif result["status"] == "done":
        status = "awaiting_review"
    else:
        status = result["status"]
    h = st["history"][-1]
    ndata = len((result or {}).get("data_requests") or [])
    h.update(ended=now(), minutes=round((time.time() - t0) / 60, 1), codex_rc=rc, check_rc=chk.returncode,
             worker_status=(result or {}).get("status"), data_requests=ndata)
    st.update(status=status, pid=None, updated=now(), check_passed=chk.returncode == 0, data_requests=ndata)
    save(job, st)
    write_review(job, n, result, chk.returncode, rc)
    notify("codex-harness", f"{job}: round {n} {status}, check {'pass' if chk.returncode == 0 else 'FAIL'}"
           + (f", {ndata} data request(s)" if ndata else ""))


def sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def codex_version() -> str:
    try:
        r = subprocess.run([CODEX, "--version"], capture_output=True, text=True, timeout=20, check=False)
        if r.returncode != 0:
            return f"(codex --version exit {r.returncode})"
        return (r.stdout or r.stderr).strip().splitlines()[0][:80] if (r.stdout or r.stderr).strip() else "(empty)"
    except (OSError, subprocess.SubprocessError) as e:
        return f"(unavailable: {e})"


def commands_section(rd: Path) -> list[str]:
    out = ["## Commands", ""]
    for name, label in (("command.json", "codex"), ("check_command.json", "check")):
        try:
            c = json.loads((rd / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out.append(f"- {label}: ({name} missing)")
            continue
        argv = " ".join(c["argv"])
        out.append(f"- {label}: `{argv}` · exit {c.get('exit_code')} · {c.get('duration_s', '?')} s"
                   + (f" · {c['codex_version']}" if c.get("codex_version") else "")
                   + f" · {(rd / name).relative_to(ROOT)}")
    out += [f"- every harness invocation (argv, actor, exit, stdout/stderr): {(HDIR / 'commands.log').relative_to(ROOT)}",
            ""]
    return out


def write_review(job: str, n: int, result: dict | None, check_rc: int, codex_rc: int) -> None:
    st = load(job)
    d = jdir(job)
    rd = d / "rounds" / str(n)
    check = (rd / "check.txt").read_text(encoding="utf-8")
    handoff = (d / "HANDOFF.md").read_text(encoding="utf-8") if (d / "HANDOFF.md").exists() else "(missing)"
    r = result or {}
    reqs = r.get("data_requests") or []
    data_lines = []
    if reqs:
        data_lines = [f"## DATA REQUESTED ({len(reqs)}): the worker needs data before it can continue", ""]
        for i, q in enumerate(reqs, 1):
            verdict, why = sql_check(q.get("sql", ""))
            data_lines += [f"### {i}. {q.get('purpose', '')}",
                           f"- tables: {', '.join(q.get('tables', []))} · expected rows: {q.get('expected_rows', '')}",
                           f"- SQL check: **{verdict}**{(' (' + why + ')') if why else ''}",
                           "```sql", q.get("sql", "").strip(), "```", ""]
        data_lines.append(f"After the user approves and the data is pulled: harness data {job} --done <files...>")
        data_lines.append("")
    lines = [
        f"# Review: {job} · round {n} · {st['status']}" + (f" · DATA REQUESTED ({len(reqs)})" if reqs else ""),
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
        *data_lines,
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
        *commands_section(rd),
        "## HANDOFF.md",
        handoff,
        "",
        f"Reply: harness feedback {job} \"...\"   |   harness accept {job}   |   harness reject {job} \"reason\"",
        f"Retrospective (every job, before closing): harness lessons {job}",
    ]
    (rd / "review.md").write_text("\n".join(lines), encoding="utf-8")


def last_round(job: str) -> Path | None:
    rs = sorted((jdir(job) / "rounds").glob("*"), key=lambda p: int(p.name)) if (jdir(job) / "rounds").exists() else []
    return rs[-1] if rs else None


def sql_check(sql: str) -> tuple[str, str]:
    """Static check of a worker data request: OK (one read-only SELECT/WITH), FLAG (look closely) or REJECT."""
    t = re.sub(r"--[^\n]*|#[^\n]*", " ", sql)
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`[^`]*`", " ", t)  # literals / quoted names
    t = t.strip().rstrip(";").strip()
    if not t:
        return "REJECT", "empty SQL"
    if ";" in t:
        return "REJECT", "more than one statement"
    words = {w.upper() for w in re.findall(r"[A-Za-z_]+", t)}
    bad = sorted(words & SQL_FORBIDDEN)
    if bad:
        return "REJECT", "writes / DDL: " + ", ".join(bad)
    first = re.match(r"\(*\s*([A-Za-z]+)", t)
    if not first or first.group(1).upper() not in {"SELECT", "WITH"}:
        return "FLAG", f"does not start with SELECT/WITH ({first.group(1) if first else '?'})"
    sus = sorted(words & SQL_SUSPECT)
    if sus:
        return "FLAG", "check keywords: " + ", ".join(sus)
    return "OK", ""


def round_result(job: str, n: int) -> dict | None:
    try:
        return json.loads((jdir(job) / "rounds" / str(n) / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def describe_file(f: Path) -> str:
    size = f"{f.stat().st_size:,} bytes"
    if f.suffix == ".parquet":
        code = ("import sys, pyarrow.parquet as pq; m = pq.ParquetFile(sys.argv[1]); "
                "print(m.metadata.num_rows, '|', ', '.join(m.schema_arrow.names))")
        for py in (sys.executable, str(ROOT / ".venv" / "bin" / "python")):
            if not Path(py).exists():
                continue
            r = subprocess.run([py, "-c", code, str(f)], capture_output=True, text=True, check=False)
            if r.returncode == 0 and "|" in r.stdout:
                rows_, cols = r.stdout.strip().split("|", 1)
                return f"{size}, {int(rows_):,} rows, columns: {cols.strip()}"
        return f"{size} (row count unavailable: no pyarrow)"
    if f.suffix in {".csv", ".tsv"}:
        with open(f, encoding="utf-8", errors="replace") as fh:
            head = fh.readline().strip()
            n = sum(1 for _ in fh)
        return f"{size}, {n:,} rows, columns: {head}"
    return size


def cmd_data(a) -> None:
    st = load(a.job)
    n = st["round"]
    reqs = (round_result(a.job, n) or {}).get("data_requests") or []
    if not a.done:
        if not reqs:
            print(f"{a.job}: no data requests in round {n}")
            return
        print(f"{a.job}: round {n} · {st['status']} · {len(reqs)} data request(s)\n")
        for i, q in enumerate(reqs, 1):
            verdict, why = sql_check(q.get("sql", ""))
            print(f"[{i}] {verdict}{(': ' + why) if why else ''}\n    purpose: {q.get('purpose', '')}\n"
                  f"    tables: {', '.join(q.get('tables', []))} · expected rows: {q.get('expected_rows', '')}\n"
                  + "\n".join("    " + ln for ln in q.get("sql", "").strip().splitlines()) + "\n")
        print(f"Pull only what the user approved (read-only, dry run first), save under "
              f"{(jdir(a.job) / 'data').relative_to(ROOT)}/, then: harness data {a.job} --done <files...>")
        return
    if st["status"] not in NEEDS_HUMAN:
        sys.exit(f"{a.job} is {st['status']}; data delivery is for a job waiting on input")
    dd = jdir(a.job) / "data"
    dd.mkdir(exist_ok=True)
    files = []
    for src in a.done:
        f = Path(src).resolve()
        if not f.is_file():
            sys.exit(f"not a file: {src}")
        if dd.resolve() not in f.parents:
            shutil.copy2(f, dd / f.name)
            f = dd / f.name
        files.append(f)
    listing = "\n".join(f"- {f.relative_to(ROOT)}: {describe_file(f)}" for f in files)
    asked = "\n".join(f"- [{i}] {q.get('purpose', '')}" for i, q in enumerate(reqs, 1)) or "(none recorded)"
    body = (f"=== DATA DELIVERED (for your data requests of round {n}) ===\n"
            f"Your requests:\n{asked}\n\nFiles (read-only; pulled by the orchestrator):\n{listing}\n"
            + (f"\nNote from the orchestrator: {a.note}\n" if a.note else "")
            + "=== END DATA ===\nContinue the task with this data. Do not query any remote source. Keep HANDOFF.md "
              "current (rewrite its one-line ## Status in place), re-run the acceptance check, and finish with the "
              "JSON result object only.")
    st.setdefault("data_delivered", []).append({"round": n, "at": now(), "files": [str(f.relative_to(ROOT))
                                                                               for f in files], "note": a.note or ""})
    save(a.job, st)
    start_round(a.job, body, resume=True, bg=a.bg, kind="data")


def cmd_lessons(a) -> None:
    """Draft for the retrospective: what went wrong in this job's rounds (facts only; the lesson text is human)."""
    st = load(a.job)
    d = jdir(a.job)
    lines = [f"# Retrospective draft: {a.job} · {st['status']} · rounds used {st['round']}/{st['max_rounds']}", "",
             "## Rounds"]
    issues = []
    for h in st["history"]:
        if h.get("kind") in {"accepted", "rejected"}:
            lines.append(f"- {h['kind']} at {h.get('at', '')}: {h.get('note', '')}")
            if h["kind"] == "rejected":
                issues.append(f"job rejected: {h.get('note', '')}")
            continue
        n = h["round"]
        r = round_result(a.job, n) or {}
        lines.append(f"- round {n} ({h.get('kind')}): {h.get('minutes', '?')} min, codex exit {h.get('codex_rc', '?')}, "
                     f"worker {h.get('worker_status', '?')}, check "
                     f"{'-' if 'check_rc' not in h else ('pass' if h['check_rc'] == 0 else 'FAIL')}"
                     + (f", {h['data_requests']} data request(s)" if h.get("data_requests") else ""))
        if h.get("codex_rc") not in (None, 0) or ("ended" in h and not r):
            issues.append(f"round {n}: codex error (exit {h.get('codex_rc')}, result JSON {'ok' if r else 'missing'})"
                          f" -> see rounds/{n}/codex.log")
        if h.get("check_rc") not in (None, 0):
            chk = (d / "rounds" / str(n) / "check.txt")
            out_ = chk.read_text(encoding="utf-8").strip().splitlines()[1:] if chk.exists() else []
            tail = [ln for ln in out_ if ln.strip()][-1:]
            issues.append(f"round {n}: acceptance check FAIL" + (f" (last line: {tail[0][:120]})" if tail else ""))
        if r.get("status") in {"needs_input", "blocked", "failed"}:
            qs = "; ".join(r.get("questions", []))[:300]
            issues.append(f"round {n}: worker {r['status']}" + (f" - questions: {qs}" if qs else ""))
        if r.get("data_requests"):
            issues.append(f"round {n}: {len(r['data_requests'])} data request(s) (data was missing from the task?)")
        if h.get("kind") in {"resume", "data"}:
            fb = (d / "rounds" / str(n) / "prompt.md").read_text(encoding="utf-8").strip()
            fb = re.sub(r"\s+", " ", re.sub(r"=== [^=]+ ===", " ", fb)).strip()
            issues.append(f"round {n}: needed a {h['kind']} round: {fb[:200]}")
    if st["round"] >= st["max_rounds"]:
        issues.append("reached max_rounds")
    lines += ["", "## What went wrong (facts from the rounds)", *([f"- {i}" for i in issues] or ["- nothing recorded"])]
    hand = (d / "HANDOFF.md").read_text(encoding="utf-8") if (d / "HANDOFF.md").exists() else ""
    m = re.search(r"^#+\s*Lessons \(draft\)\s*\n(.*?)(?=^#+\s|\Z)", hand, re.M | re.S)
    lines += ["", "## Worker's Lessons (draft) from HANDOFF.md", (m.group(1).strip() if m else "") or "(none)"]
    lines += ["", "## Next", f"- Write entries (Problem / Cause / Fix / Prevent / Seen, [who] [area]): workflow ->"
              f" {HARNESS_LESSONS}; domain -> {project_lessons_path(st) or 'the project lessons file'}. "
              "Cause must be verified. The orchestrator approves and commits."]
    text = "\n".join(lines) + "\n"
    (d / "retro.md").write_text(text, encoding="utf-8")
    print(text)


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


LOG_MARKERS = ("codex", "exec", "thinking")


def log_activity(log: Path, width: int = 90) -> str:
    """Last meaningful event in a codex.log: agent message, command, or file edit (trimmed, one line)."""
    try:
        with open(log, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 200_000))
            lines = f.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    def nxt(i: int) -> str:
        for ln in lines[i + 1:i + 6]:
            if ln.strip():
                return ln.strip()
        return ""

    text = ""
    for i in range(len(lines) - 1, -1, -1):
        ln = lines[i].strip()
        if ln == "codex" and nxt(i):
            text = "says: " + nxt(i)
        elif ln == "thinking" and nxt(i):
            text = "thinking: " + nxt(i)
        elif ln == "exec" and nxt(i):
            cmd = re.sub(r"^/bin/(ba|z)?sh -lc ", "", nxt(i))
            text = "runs: " + re.sub(r" in /\S+$", "", cmd).strip("'\"")
        elif ln.startswith("diff --git "):
            text = "edits: " + ln.split(" b/", 1)[-1]
        elif ln.startswith("tokens used"):
            text = "finished: " + ln
        if text:
            break
    if not text:  # unknown format: last non-blank line
        text = next((ln.strip() for ln in reversed(lines) if ln.strip()), "")
    text = re.sub(r"\s+", " ", text)
    return text if len(text) <= width else text[:width - 1] + "…"


def rows() -> list[dict]:
    out = []
    for d in sorted((HDIR / "jobs").glob("*")) if (HDIR / "jobs").is_dir() else []:
        try:
            st = json.loads((d / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if st["status"] == "running" and st.get("pid") and not alive(st["pid"]):
            st["status"] = "error"  # worker died without writing its result
        hand, hand_age = "", ""
        if (d / "HANDOFF.md").exists():
            t = (d / "HANDOFF.md").read_text(encoding="utf-8")
            m = re.search(r"^#+\s*Status\s*\n+\s*(.+)", t, re.M)
            hand = (m.group(1) if m else "").strip("*` ")
            hand_age = str(int((time.time() - (d / "HANDOFF.md").stat().st_mtime) // 60))
        last = st["history"][-1] if st["history"] else {}
        mins = ""  # running: minutes since the round started; stopped: how long the last round took
        if st["status"] == "running" and last.get("started"):
            mins = str(int((dt.datetime.now() - dt.datetime.fromisoformat(last["started"])).total_seconds() // 60))
        elif "minutes" in last or any("minutes" in h for h in st["history"]):
            mins = str(round(next(h["minutes"] for h in reversed(st["history"]) if "minutes" in h)))
        log = d / "rounds" / str(st["round"]) / "codex.log"
        status = st["status"]
        if st.get("data_requests") and status in NEEDS_HUMAN:
            status = f"{status} +{st['data_requests']}data"
        out.append({"job": st["job"], "status": status, "base": st["status"], "round": st["round"], "min": mins,
                    "check": {True: "pass", False: "FAIL"}.get(st.get("check_passed"), "-"), "handoff": hand,
                    "handoff_age": hand_age, "log": log_activity(log) if log.exists() else ""})
    return out


def table(rs: list[dict]) -> str:
    head = f"{'JOB':22} {'STATUS':20} {'RND':>3} {'MIN':>4} {'CHECK':5}  HANDOFF STATUS (age, min)"
    body = []
    for r in rs:
        age = f" ({r['handoff_age']}m)" if r["handoff_age"] else ""
        body.append(f"{r['job'][:22]:22} {r['status']:20} {r['round']:>3} {r['min']:>4} {r['check']:5}  "
                    f"{r['handoff'][:64]}{age}")
        if r["log"]:
            body.append(f"{'':22} └ log: {r['log']}")
    return "\n".join([head, "-" * len(head + " " * 40), *body]) if body else "(no jobs)"


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
            wait = [r["job"] for r in rs if r["base"] in NEEDS_HUMAN]
            if wait:
                print(f"\nWaiting for you: {', '.join(wait)}   ->  harness review <job>")
            data = [r["job"] for r in rs if "data" in r["status"]]
            if data:
                print(f"DATA REQUESTED: {', '.join(data)}   ->  harness data <job>")
            for r in rs:
                key = f"{r['status']}#{r['round']}"
                if r["base"] in NEEDS_HUMAN and told.get(r["job"]) != key:
                    notify("codex-harness", f"{r['job']} needs you: {r['status']} (round {r['round']})")
                told[r["job"]] = key
            time.sleep(a.seconds)
    except KeyboardInterrupt:
        pass


class Tee(io.TextIOBase):
    """Writes to the real stream and keeps a copy (capped for long-running monitor) for commands.log."""

    def __init__(self, real, cap: int | None = None):
        self.real, self.cap, self.buf = real, cap, []
        self.size = 0

    def write(self, text: str) -> int:
        self.real.write(text)
        self.buf.append(text)
        self.size += len(text)
        if self.cap and self.size > 2 * self.cap:
            joined = "".join(self.buf)[-self.cap:]
            self.buf, self.size = [joined], len(joined)
        return len(text)

    def flush(self) -> None:
        self.real.flush()

    def isatty(self) -> bool:
        return self.real.isatty()

    def text(self) -> str:
        t = "".join(self.buf)
        return t[-self.cap:] if self.cap else t


def log_command(argv: list[str], job, rc, t0: float, out: str, err: str) -> None:
    try:
        if not HDIR.is_dir():
            return
        rec = {"ts": dt.datetime.fromtimestamp(t0).isoformat(timespec="seconds"), "argv": argv, "cwd": os.getcwd(),
               "actor": os.environ.get("HARNESS_ACTOR", "unknown"), "job": job, "exit_code": rc,
               "duration_s": round(time.time() - t0, 2), "stdout": out, "stderr": err}
        with open(HDIR / "commands.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - logging must never fail the command
        pass


def main() -> None:
    t0, argv = time.time(), [sys.argv[0], *sys.argv[1:]]
    monitor = len(sys.argv) > 1 and sys.argv[1] == "monitor"
    out, err = Tee(sys.stdout, 20_000 if monitor else None), Tee(sys.stderr, 20_000 if monitor else None)
    real_out, real_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    rc, job = 0, None
    try:
        job = _main()
    except SystemExit as e:
        if e.code is None or isinstance(e.code, int):
            rc = e.code or 0
        else:
            print(e.code, file=sys.stderr)
            rc = 1
    except KeyboardInterrupt:
        rc = 130
    except BaseException:
        import traceback
        traceback.print_exc()
        rc = 1
    finally:
        sys.stdout.flush()
        sys.stdout, sys.stderr = real_out, real_err
        if job is None and len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
            job = sys.argv[2] if sys.argv[1] not in {"init", "status", "monitor"} else None
        log_command(argv, job, rc, t0, out.text(), err.text())
    sys.exit(rc)


def _main():
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
    s.add_argument("--lessons", help="project lessons file (default: first of " + ", ".join(PROJECT_LESSONS) + ")")
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
    s = sub.add_parser("lessons", help="retrospective draft: what went wrong in the job's rounds")
    s.add_argument("job")
    s.set_defaults(f=cmd_lessons)
    s = sub.add_parser("data", help="list the worker's data requests, or deliver pulled files with --done")
    s.add_argument("job")
    s.add_argument("--done", nargs="+", metavar="FILE")
    s.add_argument("--note")
    s.add_argument("--bg", action="store_true")
    s.set_defaults(f=cmd_data)
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
    return getattr(a, "job", None)


if __name__ == "__main__":
    main()
