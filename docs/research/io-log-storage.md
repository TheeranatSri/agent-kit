# agent-io-log storage: JSONL vs SQLite (measured 2026-10-08)

Question (user): can the io-log live in SQLite, and how do insert and read compare with reading JSONL directly?

Data: the real log (844 records over 3 days, average 19 KB per record because `text` and tool previews are stored),
repeated x1 / x10 / x100. x100 = 84k records ≈ 300 days at today's rate. Script:
`python3 -I optional/agent-io-log/bench_storage.py <scratch dir> 1 10 100` (writes ~3.5 GB at x100; delete after).

| records | size JSONL / SQLite | write per hook call (3 records) JSONL / SQLite | token report by actor: JSONL scan / SQLite |
|---|---|---|---|
| 844 | 17 / 18 MB | 0.49 / 1.9 ms | 59 ms / 3.7 ms |
| 8,440 | 174 / 181 MB | 0.41 / 1.8 ms | 612 ms / 31 ms |
| 84,400 | 1.7 / 1.8 GB | 0.38 / 2.1 ms | 6.5 s / 55 ms warm, 495 ms cold; 7 ms with a covering index |

- Totals from SQLite equal the JSONL scan at every size (checked in the script).
- Writes: SQLite costs ~1.5 ms more per hook call (open, WAL transaction, close). The hook is a new Python process
  each time (~30-50 ms start-up), so this does not matter.
- Reads: the gain needs the numbers in real columns. Querying the JSON text (`json_extract`, or `LIKE` on it) is as
  slow as the JSONL scan or slower (10.2 s at x100), because every 19 KB row is read.
- Size: about the same (+4%). The big part is the text, not the format.

Options:
A) SQLite only (columns for ts / event / project / session / actor / model / token counts + the full JSON in `data`).
B) Keep JSONL as the append-only source, add `index.db` built incrementally by the report script (rebuildable at any time, JSONL stays greppable for any model).
C) Keep JSONL; it is fine for months at today's volume (6.5 s only after ~a year).
