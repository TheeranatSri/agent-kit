#!/usr/bin/env bash
# agent-kit installer. Idempotent: safe to run again after `git pull`.
# Usage: ./install.sh [--with-io-log] [--dry-run]
# Needs: python3, Claude Code (`claude`), Codex CLI (`codex`). Never deletes anything:
# an existing file that differs is moved to <file>.bak-<timestamp> first.
set -euo pipefail

KIT="$(cd "$(dirname "$0")" && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
WITH_IO_LOG=0
DRY=0
for a in "$@"; do
  case "$a" in
    --with-io-log) WITH_IO_LOG=1 ;;
    --dry-run) DRY=1 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

run() { if [ "$DRY" = 1 ]; then echo "DRY: $*"; else "$@"; fi; }
say() { printf '\n== %s\n' "$*"; }

# Copy src to dst; back up dst first when it exists and differs.
put() {
  local src="$1" dst="$2"
  if [ -e "$dst" ] && ! diff -rq "$src" "$dst" >/dev/null 2>&1; then
    run mv "$dst" "$dst.bak-$TS"; echo "backup: $dst.bak-$TS"
  fi
  if [ -e "$dst" ]; then echo "same:   $dst"; return; fi
  run mkdir -p "$(dirname "$dst")"
  run cp -R "$src" "$dst"; echo "copied: $dst"
}

# Symlink dst -> src unless dst already points there; back up a real file/dir in the way.
link() {
  local src="$1" dst="$2"
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then echo "linked: $dst"; return; fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then run mv "$dst" "$dst.bak-$TS"; echo "backup: $dst.bak-$TS"; fi
  run mkdir -p "$(dirname "$dst")"
  run ln -s "$src" "$dst"; echo "link:   $dst -> $src"
}

say "prerequisites"
for c in python3 claude codex git; do
  if command -v "$c" >/dev/null; then echo "ok:      $c"; else echo "MISSING: $c"; fi
done

say "tools in ~/tools (paths used by CLAUDE.md, AGENTS.md and the skills)"
link "$KIT/codex-harness" "$HOME/tools/codex-harness"
link "$KIT/claude-mods" "$HOME/tools/claude-mods"
link "$HOME/tools/codex-harness/harness.py" "$HOME/.local/bin/harness"
run chmod +x "$KIT/codex-harness/harness.py"

say "Claude Code: global CLAUDE.md and user skills"
put "$KIT/claude-home/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
for s in "$KIT"/claude-home/skills/*/; do
  s="${s%/}"; put "$s" "$HOME/.claude/skills/$(basename "$s")"
done

say "shared skills (agent-kit/skills) -> Claude and Codex, as links so git pull updates both"
for s in "$KIT"/skills/*/; do
  s="${s%/}"; n="$(basename "$s")"
  link "$s" "$HOME/.claude/skills/$n"
  link "$s" "$HOME/.codex/skills/$n"
done

say "Codex: global AGENTS.md"
put "$KIT/codex-home/AGENTS.md" "$HOME/.codex/AGENTS.md"

say "node on Claude Code's PATH (Codex plugin hooks run 'node' via /bin/sh, lesson L16)"
if [ -e "$HOME/.local/bin/node" ]; then
  echo "ok:      ~/.local/bin/node exists"
elif ls -d "$HOME"/.nvm/versions/node/v* >/dev/null 2>&1; then
  NODE="$(ls -d "$HOME"/.nvm/versions/node/v* | sort -V | tail -1)/bin/node"
  link "$NODE" "$HOME/.local/bin/node"
  echo "note:    pinned to $NODE; re-point after an nvm version change"
elif command -v node >/dev/null && [ "$(command -v node)" != "$HOME/.local/bin/node" ]; then
  echo "ok:      node at $(command -v node) (check it is on Claude Code's PATH too)"
else
  echo "MISSING: node (install Node, e.g. via nvm, then run this again)"
fi

say "Claude Code plugins: codex (OpenAI) + clear-guard, wiki-note (local)"
claude_plugin() { if [ "$DRY" = 1 ] || [ "${SKIP_PLUGINS:-0}" = 1 ]; then echo "DRY: claude plugin $*"; else claude plugin "$@" 2>&1 | tail -2; fi; }
claude_plugin marketplace add openai/codex-plugin-cc || true
claude_plugin install codex@openai-codex --scope user || true
claude_plugin marketplace add "$HOME/tools/claude-mods" || true
claude_plugin install clear-guard@local-mods --scope user || true
claude_plugin install wiki-note@local-mods --scope user || true

if [ "$WITH_IO_LOG" = 1 ]; then
  say "optional: agent-io-log hooks (UserPromptSubmit / Stop / SubagentStop)"
  link "$KIT/optional/agent-io-log" "$HOME/tools/agent-io-log"
  SETTINGS="$HOME/.claude/settings.json"
  if [ "$DRY" = 1 ]; then echo "DRY: add io-log hooks to $SETTINGS"; else
    python3 - "$SETTINGS" "$HOME/tools/agent-io-log/agent_io_log.py" "$TS" <<'PY'
import json, os, shutil, sys
path, script, ts = sys.argv[1], sys.argv[2], sys.argv[3]
s = json.load(open(path)) if os.path.exists(path) else {}
cmd = f"/usr/bin/env python3 {script} hook"
hooks = s.setdefault("hooks", {})
changed = False
for ev in ("UserPromptSubmit", "Stop", "SubagentStop"):
    groups = hooks.setdefault(ev, [])
    if any("agent_io_log.py" in h.get("command", "") for g in groups for h in g.get("hooks", [])):
        print(f"same:   {ev} hook"); continue
    groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": 30}]})
    print(f"added:  {ev} hook"); changed = True
if changed:
    if os.path.exists(path):
        shutil.copy(path, f"{path}.bak-{ts}"); print(f"backup: {path}.bak-{ts}")
    json.dump(s, open(path, "w"), indent=2)
PY
  fi
fi

say "checks"
if [ "$DRY" = 1 ]; then echo "DRY: skipped"; exit 0; fi
"$HOME/.local/bin/harness" --help >/dev/null && echo "ok:      harness --help"
case ":$PATH:" in *":$HOME/.local/bin:"*) echo "ok:      ~/.local/bin on PATH" ;;
  *) echo "WARN:    ~/.local/bin not on PATH; add: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;; esac
if [ "${SKIP_PLUGINS:-0}" != 1 ]; then
  claude plugin list 2>&1 | grep -E "clear-guard|wiki-note|codex@" || true
  claude plugin test "$HOME/tools/claude-mods/clear-guard" 2>&1 | tail -3 || true
  claude plugin test "$HOME/tools/claude-mods/wiki-note" 2>&1 | tail -3 || true
fi
echo; echo "done. Start a new Claude Code session (or /reload-plugins) to load the plugins."
