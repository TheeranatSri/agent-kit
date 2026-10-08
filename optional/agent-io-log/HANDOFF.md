# Status
Built and installed: hooks active, today's backfill verified (2026-10-08).

# Done
- agent_io_log.py (hook + --backfill [--since]), README.md.
- Hooks UserPromptSubmit/Stop/SubagentStop merged into ~/.claude/settings.json (backup settings.json.bak-20261008-114339), JSON validated.
- Backfill today: 224 events; second run 0. user_input for session 61309df7 = 37 = direct count of origin.kind=human (local date 2026-10-08).
- Hook tested with sample payloads for all 3 events, exit 0, garbage stdin ok.

# Next
- User to evaluate log size (full tool results) and decide on truncation.
- Optional: backfill older days (`--backfill`); Codex project slug uses session cwd.

# How to verify
Run `python3 agent_io_log.py --backfill --since 2026-10-08` (appends 0); inspect ~/agent-io-logs/2026-10-08/*.jsonl; `cat ~/agent-io-logs/_errors.log`.
