"""JSONL vs SQLite for agent-io-log: write cost per hook call and report read cost, on the real log x N."""
import glob, json, os, sqlite3, sys, time, collections
SRC = os.path.expanduser("~/agent-io-logs")
OUT = sys.argv[1]
recs = [json.loads(l) for f in sorted(glob.glob(f"{SRC}/*/*.jsonl")) for l in open(f, encoding="utf-8")]
KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
print(f"real records: {len(recs)}, avg json bytes: {sum(len(json.dumps(r, ensure_ascii=False)) for r in recs)//len(recs)}")

def run(mult, batch=3):
    data = recs * mult
    jl, db = f"{OUT}/x{mult}.jsonl", f"{OUT}/x{mult}.db"
    for p in (jl, db, db + "-wal", db + "-shm"):
        if os.path.exists(p): os.remove(p)
    # write: one hook call = open, append `batch` records, close (like write_recs)
    t = time.perf_counter()
    for i in range(0, len(data), batch):
        with open(jl, "a", encoding="utf-8") as f:
            for r in data[i:i + batch]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    w_jl = time.perf_counter() - t
    t = time.perf_counter()
    con = sqlite3.connect(db); con.execute("PRAGMA journal_mode=WAL"); con.execute("PRAGMA synchronous=NORMAL")
    con.execute("""CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, ts TEXT, event TEXT, project TEXT,
      session TEXT, actor TEXT, model TEXT, in_tok INT, out_tok INT, cache_read INT, cache_write INT, data TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_ts ON events(ts)"); con.execute("CREATE INDEX IF NOT EXISTS ix_proj ON events(project, ts)")
    con.close()
    for i in range(0, len(data), batch):
        con = sqlite3.connect(db); con.execute("PRAGMA synchronous=NORMAL")  # each hook is a new process
        with con:
            con.executemany("INSERT INTO events(ts,event,project,session,actor,model,in_tok,out_tok,cache_read,cache_write,data) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(r.get("ts"), r.get("event"), r.get("project"), r.get("session"), r.get("actor"), r.get("model"),
                  *[int((r.get("usage") or {}).get(k) or 0) for k in KEYS], json.dumps(r, ensure_ascii=False)) for r in data[i:i + batch]])
        con.close()
    w_db = time.perf_counter() - t
    calls = len(range(0, len(data), batch))
    # read: token report by actor
    t = time.perf_counter()
    tot = collections.defaultdict(lambda: [0] * 5)
    for line in open(jl, encoding="utf-8"):
        d = json.loads(line); u = d.get("usage")
        if not u or d.get("event") not in ("assistant_output", "agent_report"): continue
        row = tot[d.get("actor")]; row[0] += 1
        for i, k in enumerate(KEYS, 1): row[i] += int(u.get(k) or 0)
    r_jl = time.perf_counter() - t
    con = sqlite3.connect(db)
    t = time.perf_counter()
    q = con.execute("""SELECT actor, count(*), sum(in_tok), sum(out_tok), sum(cache_read), sum(cache_write) FROM events
      WHERE event IN ('assistant_output','agent_report') AND data LIKE '%"usage": {%' GROUP BY actor""").fetchall()
    r_db = time.perf_counter() - t
    t = time.perf_counter()
    q2 = con.execute("""SELECT json_extract(data,'$.actor'), sum(json_extract(data,'$.usage.output_tokens')) FROM events
      WHERE json_extract(data,'$.event') IN ('assistant_output','agent_report') GROUP BY 1""").fetchall()
    r_dbj = time.perf_counter() - t
    t = time.perf_counter()
    q3 = con.execute("SELECT count(*) FROM events WHERE project=? AND ts>=?", (data[0]["project"], "2026-10-08")).fetchone()
    r_ix = time.perf_counter() - t
    con.close()
    agree = {a: r[2] for a, r in tot.items()} == {a: o for a, _, _, o, _, _ in q}
    mb = lambda p: os.path.getsize(p) / 1e6
    print(f"x{mult:<4} records {len(data):>7}  size jsonl {mb(jl):7.1f} MB  sqlite {mb(db):7.1f} MB | "
          f"write per hook call: jsonl {w_jl/calls*1e3:.3f} ms  sqlite {w_db/calls*1e3:.3f} ms | "
          f"report: jsonl scan {r_jl*1e3:8.1f} ms  sql cols {r_db*1e3:7.1f} ms  sql json_extract {r_dbj*1e3:7.1f} ms  "
          f"indexed filter {r_ix*1e3:.2f} ms | totals agree: {agree}")

for m in map(int, sys.argv[2:]): run(m)
