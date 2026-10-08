#!/usr/bin/env bash
# SessionStart hook (startup|clear): print the handoff context so the new session starts
# with it. stdout of a SessionStart hook is added to the model's context. Read-only.
# Paths come from .claude/handoff.json (see handoff_config.sh).
set -u
export DEVELOPER_DIR="${DEVELOPER_DIR:-/Library/Developer/CommandLineTools}"  # harness lesson L12

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$root" || exit 0
. "$root/.claude/hooks/handoff_config.sh"

section() {  # section <file> <heading regex>: body of the first matching "## " section
  awk -v re="$2" '$0 ~ "^## " re {f=1;next} /^## /{f=0} f' "$1"
}

log="$SESSION_LOG"
echo "# Handoff context (auto, SessionStart hook)"
echo
echo "Before work: read $(printf '%s' "$LESSONS" | paste -sd ',' - | sed 's/,/ and /g')."
[ -f "$WIKI_DIR/index.md" ] && echo "Project knowledge: read $WIKI_DIR/index.md first (wiki rule)."
echo "Branch: $(git branch --show-current 2>/dev/null)  | uncommitted files: $(git status --short 2>/dev/null | wc -l | tr -d ' ')"
echo
if [ -n "$log" ]; then
  echo "## Session log: $log (updated $(date -r "$log" '+%Y-%m-%d %H:%M'))"
  echo "### Status"
  section "$log" "Status" | head -20
  echo "### Open"
  section "$log" "Open" | head -30
else
  echo "No session log yet ($SESSION_LOG_GLOB); /handoff creates one."
fi

op=".harness/OPERATOR_HANDOFF.md"
if [ -f "$op" ]; then
  echo
  echo "## $op Status (updated $(date -r "$op" '+%Y-%m-%d %H:%M'))"
  section "$op" "Status" | head -8
fi

if command -v harness >/dev/null && [ -d .harness/jobs ]; then
  echo
  echo "## harness status"
  harness status 2>&1 | head -20
fi

# Auto snapshots newer than the session log mean the last session ended without /handoff.
if [ -d .claude/handoff-auto ]; then
  newer="$(find .claude/handoff-auto -name 'handoff-auto-*.md' ${log:+-newer "$log"} 2>/dev/null | sort | tail -3)"
  if [ -n "$newer" ]; then
    echo
    echo "## WARNING: last session ended without /handoff. Read these snapshots first:"
    echo "$newer"
  fi
fi
exit 0
