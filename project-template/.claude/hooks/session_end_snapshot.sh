#!/usr/bin/env bash
# SessionEnd hook: safety net for handoff.
# If the session log was not updated in the last STALE_MIN minutes when the session ends
# (/clear, exit, logout), write a plain snapshot to .claude/handoff-auto/ so the next session
# can see what state was left behind. No LLM, never blocks, never edits tracked files.
# Paths come from .claude/handoff.json (see handoff_config.sh); HANDOFF_STALE_MIN overrides staleMin.
set -u
export DEVELOPER_DIR="${DEVELOPER_DIR:-/Library/Developer/CommandLineTools}"  # harness lesson L12

input="$(cat)"
root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$root" || exit 0
. "$root/.claude/hooks/handoff_config.sh"
STALE_MIN="${HANDOFF_STALE_MIN:-$STALE_MIN}"

field() { printf '%s' "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get('$1') or '$2')" 2>/dev/null; }
reason="$(field reason unknown)"
session_id="$(field session_id '')"
transcript="$(field transcript_path '')"

log="$SESSION_LOG"
if [ -n "$log" ] && [ -z "$(find "$log" -mmin +"$STALE_MIN" 2>/dev/null)" ]; then
  exit 0  # session log is fresh: the handoff was written
fi

out_dir=".claude/handoff-auto"
mkdir -p "$out_dir"
ts="$(date +%Y-%m-%dT%H%M%S)"
out="$out_dir/handoff-auto-$ts.md"
{
  echo "# Auto handoff snapshot ($ts)"
  echo
  echo "Session ended (reason: $reason) without a fresh session log (older than $STALE_MIN min)."
  echo "Session: $session_id"
  echo "Transcript: $transcript"
  echo "Session log: ${log:-none}"
  echo
  echo "## Session log Status (as left)"
  [ -n "$log" ] && awk '/^## Status/{f=1;next} /^## /{f=0} f' "$log"
  echo
  echo "## Git"
  echo "Branch: $(git branch --show-current 2>/dev/null)"
  echo '```'
  git status --short 2>/dev/null | head -40
  echo '---'
  git log --oneline -5 2>/dev/null
  echo '```'
  echo
  echo "## harness status"
  echo '```'
  command -v harness >/dev/null && harness status 2>&1 | head -30
  echo '```'
} > "$out"
exit 0
