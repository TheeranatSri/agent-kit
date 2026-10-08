#!/usr/bin/env bash
# Run on the machine where the tools live as real folders (the original one): copies the live files into the kit
# so they can be committed and pushed. Shows `git status` at the end; it never commits.
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"

sync_repo() {  # ~/tools/<name> is its own git repo: pull its commits into the kit (history kept)
  local name="$1" src="$HOME/tools/$1"
  if [ -L "$src" ]; then echo "skip $name: ~/tools/$name is already a link to the kit"; return; fi
  [ -d "$src/.git" ] || { echo "skip $name: $src is not a git repo"; return; }
  if [ -n "$(git -C "$src" status --porcelain --untracked-files=no)" ]; then
    echo "STOP $name: uncommitted changes in $src; commit them there first"; return 1
  fi
  (cd "$KIT" && git fetch -q "$src" main && git merge -q -X subtree="$name" --allow-unrelated-histories \
    -m "chore: sync $name from ~/tools/$name" FETCH_HEAD) && echo "merged $name"
}

sync_repo codex-harness
sync_repo claude-mods

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
