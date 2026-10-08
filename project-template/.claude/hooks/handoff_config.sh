#!/usr/bin/env bash
# Sourced by the SessionStart / SessionEnd hooks. Reads .claude/handoff.json (the same file clear-guard reads)
# and sets SESSION_LOG_GLOB, STALE_MIN, WIKI_DIR, LESSONS (newline separated). Missing file or keys = defaults.
# Also sets SESSION_LOG = newest file matching the glob (by mtime), or empty.
_cfg="$(python3 - "${CLAUDE_PROJECT_DIR:-.}/.claude/handoff.json" <<'PY' 2>/dev/null
import json, os, shlex, sys
c = {}
try:
    c = json.load(open(sys.argv[1]))
except Exception:
    pass
log = c.get("sessionLog") or "notebooks/knowledge/session-log-*.md"
stale = c.get("staleMin") if isinstance(c.get("staleMin"), (int, float)) and c.get("staleMin") > 0 else 30
wiki = c.get("wikiDir") or os.path.dirname(log) or "."
lessons = c.get("lessons") or [os.path.join(wiki, "lessons.md"), "~/tools/codex-harness/LESSONS.md"]
print(f"SESSION_LOG_GLOB={shlex.quote(log)}")
print(f"STALE_MIN={int(stale)}")
print(f"WIKI_DIR={shlex.quote(wiki)}")
print(f"LESSONS={shlex.quote(chr(10).join(lessons))}")
PY
)"
if [ -n "$_cfg" ]; then eval "$_cfg"; else
  SESSION_LOG_GLOB="notebooks/knowledge/session-log-*.md"; STALE_MIN=30; WIKI_DIR="notebooks/knowledge"
  LESSONS="notebooks/knowledge/lessons.md"
fi
# shellcheck disable=SC2086  # the glob must expand
SESSION_LOG="$(ls -t $SESSION_LOG_GLOB 2>/dev/null | head -1)"
unset _cfg
