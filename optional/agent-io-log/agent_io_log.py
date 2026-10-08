#!/usr/bin/env python3
"""Raw event log of Claude Code and Codex work. Local only, stdlib only, zero LLM calls.

  agent_io_log.py hook                      Claude Code hook (payload on stdin; always exits 0)
  agent_io_log.py --backfill [--since DATE] ingest all transcripts/rollouts (flushes open turns)

Layout: ~/agent-io-logs/<YYYY-MM-DD>/<project-slug>.jsonl, one JSON event per line.
Thinking blocks are never read into the log. See README.md.
"""
import fcntl, glob, json, os, re, subprocess, sys, time, traceback
from datetime import datetime

HOME = os.path.expanduser("~")
CLAUDE = HOME + "/.claude/projects"
CODEX = HOME + "/.codex/sessions"
OUT = HOME + "/agent-io-logs"
STATE = OUT + "/_state.json"
SKCACHE = OUT + "/_skill_cache.json"
ERRLOG = OUT + "/_errors.log"
CODEX_RECENT = 86400
SYS_MARKERS = ("<task-notification>", "SYSTEM NOTIFICATION", "<system-reminder>", "[Request interrupted",
               "<local-command", "<command-name>", "This session is being continued")
REJ = ("doesn't want to proceed", "The tool use was rejected")
CLAIM = re.compile(r"Claim:\s*(.+?)\s*\|\s*Status:\s*(.+?)\s*\|\s*Evidence:\s*(.+)", re.I)
COMMIT = re.compile(r"\[[\w/.\-+@]+(?: \(root-commit\))? ([0-9a-f]{7,40})\]")


KINDS = {  # line keyword -> (record field, first-part field, keyed fields {lowercase key: field})
    "claim": ("claims", "statement", {"status": "status", "evidence": "evidence"}),
    "proposal": ("proposals", "id", {"options": "options", "recommend": "recommend", "rationale": "rationale"}),
    "decision": ("decisions", "id", {"choice": "choice", "by": "by", "note": "note"}),
    "question": ("questions", "id", {"to": "to", "from": "from", "text": "text"}),
    "assumption": ("assumptions", "text", {"rationale": "rationale", "risk": "risk", "revisit": "revisit"}),
    "failure": ("failures", None, {"want": "want", "actual": "actual", "evidence": "evidence", "cause": "cause", "status": "status"}),
    "done": ("done", "text", {"verified": "verified", "commit": "commit"}),
    "check": ("checks", "step", {"criterion": "criterion", "actual": "actual", "evidence": "evidence", "pass": "pass"}),
}
LINE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?`*\s*(Claim|Proposal|Decision|Question|Assumption|Failure|Done|Check)\s*:\s*(.*?)`*\s*$", re.I)
KEYED = re.compile(r"^([A-Za-z]+)\s*:\s*(.*)$", re.S)
BARE = re.compile(r"^(want|actual|evidence|cause)\b[:\s]+(.*)$", re.I | re.S)


def parse_structured(text):
    out = {v[0]: [] for v in KINDS.values()}
    for ln in (text or "").splitlines():
        m = LINE.match(ln)
        if not m:
            continue
        kind = m.group(1).lower()
        field, first, keyed = KINDS[kind]
        rec, raw, firstdone = {}, [], first is None
        for part in re.split(r"\s+\|\s+", m.group(2)):
            part = part.strip().strip("`")
            km = KEYED.match(part)
            key = km.group(1).lower() if km else None
            if km and key in keyed:
                rec[keyed[key]] = km.group(2).strip()
            elif kind == "failure" and BARE.match(part):
                bm = BARE.match(part)
                rec[keyed[bm.group(1).lower()]] = bm.group(2).strip()
            elif not firstdone:
                rec[first] = part
                firstdone = True
            elif kind == "check" and "item" not in rec:
                rec["item"] = part
            elif kind == "question" and "text" not in rec:
                rec["text"] = part
            elif part:
                raw.append(part)
        if raw:
            rec["raw"] = " | ".join(raw)
        out[field].append(rec)
    return out


def err(msg):
    try:
        os.makedirs(OUT, exist_ok=True)
        with open(ERRLOG, "a") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except Exception:
        pass


def cut(s, n):
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def preview(inp, n=120):
    if not isinstance(inp, dict):
        return cut(str(inp).replace("\n", " "), n)
    for k in ("description", "command", "file_path", "pattern", "path", "url", "query", "prompt", "skill"):
        if inp.get(k):
            return cut(str(inp[k]).replace("\n", " "), n)
    return cut(json.dumps(inp, ensure_ascii=False), n)


def slug(p):
    return re.sub(r"[/._]", "-", p)


def short_proj(s):
    return s.replace("-Users-theeranat-sri-", "", 1) or s


def blocks_text(c):
    if isinstance(c, str):
        return c
    return "\n".join(b.get("text", "") for b in c or [] if isinstance(b, dict) and b.get("type") == "text")


def pts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()


def iso(ts):
    return pts(ts).isoformat(timespec="seconds")


# ---------------------------------------------------------------- git + skills (cached)
_git = {}


def git_info(cwd):
    """(branch, worktree) for cwd; worktree = basename of the linked worktree path else ''."""
    if not cwd:
        return None, ""
    if cwd in _git:
        return _git[cwd]
    b, w = None, ""
    if os.path.isdir(cwd):
        def g(*a):
            return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, timeout=5).stdout.strip()
        try:
            b = g("branch", "--show-current") or None
            gd, cd = g("rev-parse", "--absolute-git-dir"), g("rev-parse", "--path-format=absolute", "--git-common-dir")
            if gd and cd and os.path.realpath(gd) != os.path.realpath(cd):
                w = os.path.basename(g("rev-parse", "--show-toplevel"))
        except Exception:
            pass
    m = re.search(r"/\.claude/worktrees/([^/]+)", cwd)
    if m and not w:
        w = m.group(1)
    _git[cwd] = (b, w)
    return b, w


_skc = None


def skill_desc(name, cwd):
    global _skc
    if _skc is None:
        try:
            _skc = json.load(open(SKCACHE))
        except Exception:
            _skc = {}
    if _skc.get(name):
        return _skc[name]
    base = name.split(":")[-1]
    cands = [f"{HOME}/.claude/skills/{base}/SKILL.md"]
    if cwd:
        cands.append(f"{cwd}/.claude/skills/{base}/SKILL.md")
    cands += glob.glob(f"{HOME}/.claude/plugins/**/skills/{base}/SKILL.md", recursive=True)
    d = ""
    for p in cands:
        if os.path.isfile(p):
            try:
                txt = open(p, encoding="utf-8").read(8000)
                m = re.match(r"---\n(.*?)\n---", txt, re.S)
                mm = m and re.search(r"^description:\s*(.*?)(?=^[\w-]+:|\Z)", m.group(1), re.S | re.M)
                if mm:
                    d = re.sub(r"\s+", " ", mm.group(1)).strip().lstrip(">|").strip().strip("\"'")
                    break
            except Exception:
                pass
    _skc[name] = d
    return d


# ---------------------------------------------------------------- turn model
def new_turn(ts, kind, text, uuid, line, e):
    return {"t0": ts, "t1": ts, "kind": kind, "input": text, "uuid": uuid, "line": line, "e": e,
            "texts": [], "tools": [], "skills": [], "spawned": [], "rej": [], "ids": {}, "usage": {}, "model": None,
            "perm": e.get("permissionMode")}


def add_tool(t, name, inp, tid, desc=None):
    rec = {"name": name, "description": desc if desc is not None else preview(inp), "input": inp,
           "result": None, "is_error": False, "rejected": False}
    t["tools"].append(rec)
    if tid:
        t["ids"][tid] = rec
    return rec


class Ctx:
    """Per-file parsing context for one ingest pass."""

    def __init__(self, info, st, out):
        self.info, self.st, self.out = info, st, out
        self.open = None
        self.pos = 0
        self.start = None
        self.start_line = 0
        self.no = st["no"]
        self.seen_first = st["seen_first"]

    def rec(self, event, ts, frm, to, text, uuid, line, e, **kw):
        i = self.info
        b, w = git_info(e.get("cwd") or i.get("cwd"))
        branch = e.get("gitBranch") or i.get("branch") or b
        r = {"ts": iso(ts), "event": event, "project": i["project"], "branch": branch, "worktree": w,
             "session": i["session"], "actor": i["actor"], "turn": self.no + (0 if event in ("user_input", "agent_prompt", "codex_input") and False else 0),
             "from": frm, "to": to, "text": text, "model": kw.pop("model", None), "usage": kw.pop("usage", None),
             "duration_s": kw.pop("duration_s", None), "permission_mode": e.get("permissionMode") or kw.pop("perm", None),
             "parent": i.get("parent"), "agent_id": i.get("agent_id"),
             "source": {"file": i["file"], "uuid": uuid, "line": line}}
        r.update(kw)
        self.out.append(r)
        return r

    def open_turn(self, ts, kind, text, uuid, line, e, from_, to, event):
        self.close()
        self.no += 1
        t = self.open = new_turn(ts, kind, text, uuid, line, e)
        t["no"] = self.no
        self.start, self.start_line = self.pos, self.line_before
        if self.st.get("inp") != uuid:  # emit the input once, even if the open turn is re-parsed
            r = self.rec(event, ts, from_, to, text, uuid, line, e)
            r["turn"] = self.no
            self.st["inp"] = uuid
        t["from"] = from_

    def close(self):
        t = self.open
        if not t:
            return
        self.open = None
        i = self.info
        if not (t["texts"] or t["tools"] or t["rej"]):
            return
        text = "\n\n".join(t["texts"])
        ev, frm = i["out_event"], i["actor"]
        to = "user" if t["kind"] in ("continuation", "task-notification", "peer-message") else t["from"]
        files = []
        for x in t["tools"]:
            if x["name"] in ("Edit", "Write", "NotebookEdit", "MultiEdit") and isinstance(x["input"], dict):
                p = x["input"].get("file_path") or x["input"].get("notebook_path")
                if p and p not in files:
                    files.append(p)
        commits = []
        for x in t["tools"]:
            if x["name"] in ("Bash", "exec") and x["result"]:
                for h in COMMIT.findall(x["result"]):
                    if h not in commits:
                        commits.append(h)
        structured = parse_structured(text)
        skills = [{"name": s["name"], "description": skill_desc(s["name"], t["e"].get("cwd") or i.get("cwd"))} for s in t["skills"]]
        dur = round((pts(t["t1"]) - pts(t["t0"])).total_seconds(), 1)
        r = self.rec(ev, t["t1"], frm, to, text, t["uuid"], t["line"], t["e"], model=t["model"],
                     usage=t["usage"] or None, duration_s=dur, perm=t["perm"], tools=t["tools"], skills=skills,
                     agents_spawned=t["spawned"], files_changed=files, commits=commits, **structured)
        r["turn"] = t["no"]
        for j in t["rej"]:
            rr = self.rec("tool_rejected", j["ts"], "user", frm, j["reason"], j["uuid"], t["line"], t["e"],
                          tool=j["tool"], description=j["description"], input=j["input"], reason=j["reason"])
            rr["turn"] = t["no"]


def claude_entry(C, d, lineno):
    t, m = d.get("type"), d.get("message")
    if t not in ("user", "assistant") or not m:
        return
    ts = d.get("timestamp")
    info = C.info
    cur = C.open
    c = m.get("content")
    if cur is not None:
        cur["t1"] = ts
    if t == "assistant":
        if cur is None:
            C.no += 1
            cur = C.open = new_turn(ts, "continuation", "", d.get("uuid"), lineno, d)
            cur["no"], cur["from"] = C.no, "user"
            C.start, C.start_line = C.pos, C.line_before
        if m.get("model"):
            cur["model"] = m["model"]
        u = m.get("usage")
        if isinstance(u, dict):
            cur.setdefault("_u", {})[m.get("id") or d.get("uuid")] = u
            tot = {}
            for uu in cur["_u"].values():
                for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                    tot[k] = tot.get(k, 0) + (uu.get(k) or 0)
            cur["usage"] = tot
        if isinstance(c, str):
            c = [{"type": "text", "text": c}]
        for b in c or []:
            bt = b.get("type")
            if bt == "text" and b.get("text", "").strip():
                cur["texts"].append(b["text"])
            elif bt == "tool_use":
                name, inp = b.get("name", "?"), b.get("input") or {}
                if name == "SubagentHandback":
                    cur["texts"].append(str(inp.get("message", "")))
                    continue
                add_tool(cur, name, inp, b.get("id"))
                if name == "Skill" and inp.get("skill") and all(x["name"] != inp["skill"] for x in cur["skills"]):
                    cur["skills"].append({"name": inp["skill"]})
                if name == "Agent":
                    cur["spawned"].append({"description": inp.get("description", ""), "subagent_type": inp.get("subagent_type"),
                                           "model": inp.get("model"), "tool_use_id": b.get("id")})
        return
    origin = (d.get("origin") or {}).get("kind")
    if isinstance(c, list) and c and all(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
        for b in c:
            rc = b.get("content")
            txt = rc if isinstance(rc, str) else blocks_text(rc)
            rec = cur["ids"].get(b.get("tool_use_id")) if cur else None
            if rec is not None:
                rec["result"] = txt
                rec["is_error"] = bool(b.get("is_error"))
            if cur is not None and any(k in txt for k in REJ):
                mm = re.search(r"the user said:\n(.*?)(?:\n\nNote:|$)", txt, re.S)
                if rec is not None:
                    rec["rejected"] = True
                cur["rej"].append({"tool": rec["name"] if rec else "?", "description": rec["description"] if rec else "",
                                   "input": rec["input"] if rec else None, "reason": mm.group(1).strip() if mm else "",
                                   "uuid": d.get("uuid"), "ts": ts})
        return
    text = blocks_text(c)
    sub = info["sub"]
    if origin == "human":
        kind, ev, frm, to = "user", "user_input", "user", info["actor"]
    elif origin == "coordinator":
        kind, ev, frm, to = "coordinator", "agent_prompt", "main", info["actor"]
    elif origin in ("task-notification", "peer"):
        kind = "task-notification" if origin == "task-notification" else "peer-message"
        ev, frm, to = "agent_report", "agent/system", info["actor"]
        s = re.search(r"<summary>(.*?)</summary>", text, re.S)
        r = re.search(r"<result>(.*)</result>", text, re.S)
        if origin == "task-notification" and r:
            text = (s.group(1) + "\n\n" if s else "") + r.group(1)
    elif origin is None and sub and not C.seen_first and isinstance(c, str):
        kind, ev, frm, to = "orchestrator", "agent_prompt", "main", info["actor"]
    else:
        return
    if sub:
        C.seen_first = True
    if cur is not None and kind == "user":
        for r in cur["rej"]:
            if not r["reason"]:
                r["reason"] = "(next typed message) " + text
    if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "image" for b in c):
        text += "\n[image attached]"
    C.open_turn(ts, kind, text, d.get("uuid"), lineno, d, frm, to, ev)


def codex_entry(C, d, lineno):
    if d.get("type") != "response_item":
        return
    p, ts = d.get("payload") or {}, d.get("timestamp")
    pt = p.get("type")
    info = C.info
    e = {"cwd": info.get("cwd"), "gitBranch": info.get("branch")}
    if pt == "message" and p.get("role") == "user":
        text = "\n".join(c.get("text", "") for c in p.get("content", []) if isinstance(c, dict))
        if text.lstrip().startswith("<") or text.startswith("# AGENTS.md") or not text.strip():
            return
        C.open_turn(ts, "prompt", text, p.get("id"), lineno, e, "orchestrator/user", info["actor"], "codex_input")
        return
    cur = C.open
    if cur is None:
        if pt in ("message", "custom_tool_call", "function_call") and p.get("role") != "developer":
            C.no += 1
            cur = C.open = new_turn(ts, "continuation", "", p.get("id"), lineno, e)
            cur["no"], cur["from"] = C.no, "user"
            C.start, C.start_line = C.pos, C.line_before
        else:
            return
    cur["t1"] = ts
    if pt == "message" and p.get("role") == "assistant":
        txt = "\n".join(c.get("text", "") for c in p.get("content", []) if isinstance(c, dict))
        if txt.strip():
            cur["texts"].append(txt)
    elif pt in ("custom_tool_call", "function_call"):
        raw = p.get("input") if pt == "custom_tool_call" else p.get("arguments")
        raw = raw if isinstance(raw, str) else json.dumps(raw or "")
        cmds = re.findall(r'cmd:\s*"((?:[^"\\]|\\.)*)"', raw) or re.findall(r'"(?:cmd|command)":\s*"((?:[^"\\]|\\.)*)"', raw)
        desc = cut(cmds[0].replace("\\n", " ").replace('\\"', '"'), 120) if cmds else cut(raw, 120)
        add_tool(cur, p.get("name", "tool"), raw, p.get("call_id"), desc)
        for sk in re.findall(r"skills/([\w\-:.]+)/SKILL\.md", raw):
            if all(x["name"] != sk for x in cur["skills"]):
                cur["skills"].append({"name": sk})
    elif pt in ("custom_tool_call_output", "function_call_output"):
        rec = cur["ids"].get(p.get("call_id"))
        o = p.get("output")
        if isinstance(o, list):
            o = "\n".join(x.get("text", "") for x in o if isinstance(x, dict))
        if rec is not None:
            rec["result"] = o if isinstance(o, str) else json.dumps(o)


# ---------------------------------------------------------------- driver
def codex_info(f):
    meta, job = {}, ""
    try:
        with open(f, "rb") as fh:
            meta = json.loads(fh.readline()).get("payload", {})
            for _ in range(60):
                l = fh.readline()
                if not l:
                    break
                m = re.search(rb"- Job: ([\w\-]+)\.", l)
                if m:
                    job = m.group(1).decode()
                    break
    except Exception:
        pass
    cwd, git = meta.get("cwd", ""), meta.get("git")
    sid = meta.get("id") or os.path.basename(f)[:-6]
    return dict(project=short_proj(slug(cwd)) if cwd else "codex-unknown", session=sid,
                actor="codex:" + (job or sid[:8]), sub=False, cwd=cwd, out_event="codex_output",
                branch=git.get("branch") if isinstance(git, dict) else None)


def claude_info(f):
    parts = f.split("/")
    if "subagents" in parts:
        i = parts.index("subagents")
        proj, sid = parts[i - 2], parts[i - 1]
        aid = os.path.basename(f)[6:-6]
        desc, tuid = aid, None
        try:
            mt = json.load(open(f[:-6] + ".meta.json"))
            desc, tuid = mt.get("description") or aid, mt.get("toolUseId")
        except Exception:
            pass
        return dict(project=short_proj(proj), session=sid, actor="agent:" + desc[:80], sub=True, agent_id=aid,
                    parent={"session": sid, "tool_use_id": tuid}, out_event="agent_report")
    return dict(project=short_proj(parts[-2]), session=os.path.basename(f)[:-6], actor="main", sub=False,
                out_event="assistant_output")


def ingest(path, kind, state, flush, out):
    st = state.setdefault(path, {"offset": 0, "line": 0, "no": 0, "seen_first": False, "inp": None})
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    if size < st["offset"]:
        st.update(offset=0, line=0, no=0, seen_first=False, inp=None)
    if size == st["offset"]:
        return
    with open(path, "rb") as f:
        f.seek(st["offset"])
        data = f.read()
    end = data.rfind(b"\n")
    if end < 0:
        return
    info = dict(codex_info(path) if kind == "codex" else claude_info(path), file=path)
    C = Ctx(info, st, out)
    lineno, pos = st["line"], st["offset"]
    C.start, C.start_line = None, lineno
    for raw in data[: end + 1].split(b"\n")[:-1]:
        C.line_before = lineno
        lineno += 1
        C.pos = pos
        pos += len(raw) + 1
        raw = raw.strip()
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except Exception:
            continue
        (claude_entry if kind == "claude" else codex_entry)(C, d, lineno)
    st["seen_first"] = C.seen_first
    if C.open is not None and not flush:
        # re-parse the open turn next time; its input event is guarded by st["inp"]
        st["offset"], st["line"] = C.start, C.start_line
        st["no"] = C.open["no"] - 1
    else:
        C.close()
        st["offset"], st["line"], st["no"] = pos, lineno, C.no


def write_recs(recs, since):
    by = {}
    for r in recs:
        day = r["ts"][:10]
        if since and day < since:
            continue
        by.setdefault((day, r["project"]), []).append(r)
    n = 0
    for (day, proj), rs in by.items():
        os.makedirs(f"{OUT}/{day}", exist_ok=True)
        rs.sort(key=lambda r: r["ts"])
        with open(f"{OUT}/{day}/{re.sub(r'[^A-Za-z0-9._-]', '_', proj)[:150]}.jsonl", "a", encoding="utf-8") as f:
            for r in rs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    return n


def run(files, flush_files, backfill=False, since=None):
    os.makedirs(OUT, exist_ok=True)
    lock = open(OUT + "/_lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        state = json.load(open(STATE))
    except Exception:
        state = {}
    out = []
    for kind, f in files:
        try:
            ingest(f, kind, state, backfill or f in flush_files, out)
        except Exception:
            err(f"ingest {f}: {traceback.format_exc(limit=3)}")
    n = write_recs(out, since)
    json.dump(state, open(STATE + ".tmp", "w"), ensure_ascii=False)
    os.replace(STATE + ".tmp", STATE)
    if _skc is not None:
        try:
            json.dump(_skc, open(SKCACHE, "w"), ensure_ascii=False)
        except Exception:
            pass
    return n


def all_files(recent_codex_only, since_ts=0):
    fs = [("claude", f) for f in glob.glob(CLAUDE + "/*/*.jsonl")]
    fs += [("claude", f) for f in glob.glob(CLAUDE + "/*/*/subagents/agent-*.jsonl")]
    fs += [("codex", f) for f in glob.glob(CODEX + "/*/*/*/rollout-*.jsonl")]
    now = time.time()
    return [(k, f) for k, f in fs
            if os.path.getmtime(f) >= since_ts and not (k == "codex" and recent_codex_only and now - os.path.getmtime(f) > CODEX_RECENT)]


def hook():
    try:
        p = json.loads(sys.stdin.read() or "{}")
    except Exception:
        p = {}
    ev = p.get("hook_event_name", "")
    tp = p.get("transcript_path")
    files, flush = [], set()
    if tp and os.path.isfile(tp):
        files.append(("claude", tp))
        files += [("claude", f) for f in sorted(glob.glob(tp[:-6] + "/subagents/agent-*.jsonl"))]
        if ev in ("Stop", "SubagentStop"):
            flush.update(f for _, f in files)
    ap = p.get("agent_transcript_path")
    if ap and os.path.isfile(ap):
        files.append(("claude", ap))
        if ev == "SubagentStop":
            flush.add(ap)
    if ev == "Stop":
        files += [x for x in all_files(True) if x[0] == "codex"]
    seen, uniq = set(), []
    for x in files:
        if x[1] not in seen:
            seen.add(x[1])
            uniq.append(x)
    run(uniq, flush)


def main():
    try:
        a = sys.argv[1:]
        if "--backfill" in a:
            since = a[a.index("--since") + 1] if "--since" in a else None
            sts = datetime.strptime(since, "%Y-%m-%d").timestamp() if since else 0
            print("appended", run(all_files(False, sts), set(), backfill=True, since=since), "events")
        elif "hook" in a:
            hook()
        else:
            print(__doc__)
    except Exception:
        err(traceback.format_exc(limit=5))
    sys.exit(0)


if __name__ == "__main__":
    main()
