#!/usr/bin/env bash
# Run on the machine where the tools live as real folders (the original one): copies the live files into the kit
# so they can be committed and pushed. Shows `git status` at the end; it never commits.
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"

sync_dir() {  # copy the tracked files of ~/tools/<name> into the kit (history stays in ~/tools; the kit gets one commit)
  local name="$1" src="$HOME/tools/$1"
  if [ -L "$src" ]; then echo "skip $name: ~/tools/$name is already a link to the kit"; return; fi
  [ -d "$src" ] || { echo "skip $name: no $src"; return; }
  rsync -a --delete --exclude .git --exclude __pycache__ --exclude .DS_Store --exclude .claude-plugin/types \
    "$src/" "$KIT/$name/" && echo "copied $name"
}

sync_dir codex-harness
sync_dir claude-mods

cp "$HOME/.claude/CLAUDE.md" "$KIT/claude-home/CLAUDE.md"
for s in "$KIT"/claude-home/skills/*/; do
  s="${s%/}"; n="$(basename "$s")"
  [ -d "$HOME/.claude/skills/$n" ] && rsync -a --delete "$HOME/.claude/skills/$n/" "$s/"
done
cp "$HOME/.codex/AGENTS.md" "$KIT/codex-home/AGENTS.md"
if [ -d "$HOME/tools/agent-io-log" ] && [ ! -L "$HOME/tools/agent-io-log" ]; then
  rsync -a --delete --exclude __pycache__ "$HOME/tools/agent-io-log/" "$KIT/optional/agent-io-log/"
fi
# keep the kit portable: no absolute home paths
grep -rl "$HOME" "$KIT/claude-home" "$KIT/codex-home" "$KIT/optional" 2>/dev/null | while read -r f; do
  sed -i '' "s#$HOME#~#g" "$f"
done

git -C "$KIT" status --short
