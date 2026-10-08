#!/usr/bin/env bash
# Add the agent-kit project template to a project: /handoff + /wiki skills, SessionStart / SessionEnd hooks,
# .claude/handoff.json (shared with clear-guard), wiki seed pages, and the rules section in CLAUDE.md.
# Usage: ./install-project.sh <project-dir> [--wiki-dir DIR] [--session-log GLOB] [--update] [--dry-run]
#   --wiki-dir     wiki folder, relative to the project (default notebooks/knowledge)
#   --session-log  session log glob (default <wiki-dir>/session-log-*.md)
#   --update       replace template files that differ (old copy kept as <file>.bak-<timestamp>); default keeps yours
# Never deletes. Existing wiki pages, handoff.json and CLAUDE.md content are never replaced.
set -euo pipefail

KIT="$(cd "$(dirname "$0")" && pwd)"
TPL="$KIT/project-template"
TS="$(date +%Y%m%d-%H%M%S)"
TODAY="$(date +%Y-%m-%d)"
DRY=0; UPDATE=0; WIKI="notebooks/knowledge"; LOG=""; DEST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --update) UPDATE=1 ;;
    --wiki-dir) WIKI="${2:?}"; shift ;;
    --session-log) LOG="${2:?}"; shift ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) DEST="$1" ;;
  esac
  shift
done
[ -n "$DEST" ] && [ -d "$DEST" ] || { echo "usage: $0 <project-dir> [options]" >&2; exit 2; }
DEST="$(cd "$DEST" && pwd)"
WIKI="${WIKI%/}"
LOG="${LOG:-$WIKI/session-log-*.md}"
PROJECT="$(basename "$DEST")"

run() { if [ "$DRY" = 1 ]; then echo "DRY: $*"; else "$@"; fi; }
say() { printf '\n== %s\n' "$*"; }

# Template file -> project; keep the project's version when it differs unless --update.
put() {
  local src="$1" dst="$2"
  if [ -e "$dst" ]; then
    if diff -q "$src" "$dst" >/dev/null 2>&1; then echo "same:    ${dst#$DEST/}"; return; fi
    if [ "$UPDATE" = 0 ]; then echo "differs: ${dst#$DEST/} (kept yours; --update replaces it)"; return; fi
    run mv "$dst" "$dst.bak-$TS"; echo "backup:  ${dst#$DEST/}.bak-$TS"
  fi
  run mkdir -p "$(dirname "$dst")"
  run cp "$src" "$dst"; echo "copied:  ${dst#$DEST/}"
}

# Seed file with {{DATE}} / {{PROJECT}} filled in; only when the project has none.
seed() {
  local src="$1" dst="$2"
  if [ -e "$dst" ]; then echo "exists:  ${dst#$DEST/} (not touched)"; return; fi
  run mkdir -p "$(dirname "$dst")"
  if [ "$DRY" = 1 ]; then echo "DRY: seed $dst"; else
    sed -e "s/{{DATE}}/$TODAY/g" -e "s/{{PROJECT}}/$PROJECT/g" "$src" > "$dst"
  fi
  echo "seeded:  ${dst#$DEST/}"
}

say "skills and hooks -> $DEST/.claude"
( cd "$TPL" && find .claude -type f ! -name handoff.json ! -name settings.json | sort ) | while read -r f; do
  put "$TPL/$f" "$DEST/$f"
done
run chmod +x "$DEST"/.claude/hooks/*.sh "$DEST/.claude/skills/wiki/wiki_lint.py"

say ".claude/handoff.json (read by clear-guard, the hooks and the skills)"
if [ -e "$DEST/.claude/handoff.json" ]; then echo "exists:  .claude/handoff.json (not touched)"
elif [ "$DRY" = 1 ]; then echo "DRY: write .claude/handoff.json (sessionLog $LOG, wikiDir $WIKI)"
else
  python3 - "$DEST/.claude/handoff.json" "$LOG" "$WIKI" <<'PY'
import json, sys
path, log, wiki = sys.argv[1:]
cfg = {"sessionLog": log, "staleMin": 30, "wikiDir": wiki,
       "lessons": [f"{wiki}/lessons.md", "~/tools/codex-harness/LESSONS.md"]}
open(path, "w").write(json.dumps(cfg, indent=2) + "\n")
PY
  echo "written: .claude/handoff.json"
fi

say ".claude/settings.json hooks (SessionStart startup|clear, SessionEnd)"
if [ "$DRY" = 1 ]; then echo "DRY: merge hooks into .claude/settings.json"; else
  python3 - "$DEST/.claude/settings.json" "$TPL/.claude/settings.json" "$TS" <<'PY'
import json, os, shutil, sys
path, tpl, ts = sys.argv[1:]
s = json.load(open(path)) if os.path.exists(path) else {}
want = json.load(open(tpl))["hooks"]
hooks = s.setdefault("hooks", {})
changed = False
for ev, groups in want.items():
    have = hooks.setdefault(ev, [])
    for g in groups:
        cmd = g["hooks"][0]["command"]
        script = cmd.rsplit("/", 1)[-1]
        if any(script in h.get("command", "") for hg in have for h in hg.get("hooks", [])):
            print(f"same:    {ev} hook ({script})"); continue
        have.append(g); changed = True
        print(f"added:   {ev} hook ({script})")
if changed:
    if os.path.exists(path):
        shutil.copy(path, f"{path}.bak-{ts}"); print(f"backup:  .claude/settings.json.bak-{ts}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(json.dumps(s, indent=2) + "\n")
PY
fi

say "wiki seed pages -> $WIKI"
for f in index.md log.md lessons.md; do seed "$TPL/wiki/$f" "$DEST/$WIKI/$f"; done

say "rules section in CLAUDE.md / AGENTS.md"
for doc in CLAUDE.md AGENTS.md; do
  dst="$DEST/$doc"
  [ "$doc" = AGENTS.md ] && [ ! -e "$dst" ] && { echo "skip:    AGENTS.md (none in the project)"; continue; }
  if [ -e "$dst" ] && grep -q -e 'agent-kit:project-rules' -e '^## Lessons and multi-model work' "$dst"; then
    echo "same:    $doc already has the rules section"; continue
  fi
  if [ "$DRY" = 1 ]; then echo "DRY: append rules section to $doc"; else
    { [ -s "$dst" ] && echo; cat "$TPL/CLAUDE-section.md"; } >> "$dst"; echo "appended: $doc"
  fi
done

say ".gitignore"
if [ -e "$DEST/.gitignore" ] && grep -qx '.claude/handoff-auto/' "$DEST/.gitignore"; then echo "same:    .claude/handoff-auto/"
else run sh -c "echo '.claude/handoff-auto/' >> '$DEST/.gitignore'"; echo "added:   .claude/handoff-auto/"; fi

say "checks"
if [ "$DRY" = 1 ]; then echo "DRY: skipped"; exit 0; fi
(cd "$DEST" && python3 .claude/skills/wiki/wiki_lint.py) || echo "WARN:    wiki_lint found problems (see above)"
(cd "$DEST" && CLAUDE_PROJECT_DIR="$DEST" .claude/hooks/session_start_context.sh >/dev/null) && echo "ok:      SessionStart hook runs"
echo; echo "done. Review with 'git -C $DEST status', then commit. Start a new Claude Code session to load the hooks."
