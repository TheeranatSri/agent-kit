#!/usr/bin/env python3
"""Check a project knowledge wiki (index.md + log.md + pages). Stdlib only, no LLM.

Usage: wiki_lint.py [--dir WIKI_DIR]   (default: wikiDir from .claude/handoff.json, else notebooks/knowledge)
Exit 0 = no errors (warnings may be printed), 1 = errors, 2 = no wiki folder.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STATUSES = {"active", "reference", "done", "superseded"}
REQUIRED = ("type", "status", "updated")
LOG_KINDS = {"ingest", "result", "decision", "lesson", "plan"}
LOG_HEAD = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (\w+) \| \S")
INDEX_LINE = re.compile(r"^- \[[^\]]+\]\(([^)#\s]+)(?:#[^)]*)?\)\s*(?:—|-)\s*(.*)$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def frontmatter(text: str) -> dict[str, str] | None:
    """Top-level `key: value` pairs of a leading --- block (values kept as raw strings)."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip("'\"")
    return fm


def wiki_dir_from_config(root: Path) -> Path:
    try:
        cfg = json.loads((root / ".claude/handoff.json").read_text())
        if cfg.get("wikiDir"):
            return root / cfg["wikiDir"]
    except (OSError, ValueError):
        pass
    return root / "notebooks/knowledge"


def lint(wiki: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    pages = sorted(p for p in wiki.rglob("*.md") if not any(part.startswith(".") for part in p.relative_to(wiki).parts))
    rel = {p.relative_to(wiki).as_posix(): p for p in pages}
    fms: dict[str, dict[str, str]] = {}

    for name, path in rel.items():
        fm = frontmatter(path.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(f"{name}: no frontmatter")
            continue
        fms[name] = fm
        for key in REQUIRED:
            if not fm.get(key):
                errors.append(f"{name}: frontmatter missing '{key}'")
        if fm.get("status") and fm["status"] not in STATUSES:
            errors.append(f"{name}: status '{fm['status']}' not in {sorted(STATUSES)}")
        if fm.get("updated") and not DATE.match(fm["updated"]):
            errors.append(f"{name}: updated '{fm['updated']}' is not YYYY-MM-DD")
        if "sources" not in fm and fm.get("type") not in ("index", "log"):
            warnings.append(f"{name}: frontmatter has no 'sources'")
        if fm.get("status") == "superseded":
            target = fm.get("superseded_by", "").split(" ")[0]  # a note may follow the path
            if not target or not (path.parent / target).exists():
                errors.append(f"{name}: superseded without a valid superseded_by ('{target}')")

    index = wiki / "index.md"
    if not index.exists():
        errors.append("index.md: missing")
        indexed: dict[str, str] = {}
    else:
        indexed = {}
        for n, line in enumerate(index.read_text(encoding="utf-8").splitlines(), 1):
            m = INDEX_LINE.match(line)
            if not m or "://" in m.group(1) or m.group(1).startswith(("~", "/")):
                continue  # links outside the wiki are not checked
            target = m.group(1)
            fields = [f.strip() for f in m.group(2).split("·")]
            # status is the first word ("superseded by [x](x.md)" -> "superseded")
            indexed[target] = fields[1].split(" ")[0] if len(fields) >= 3 else ""
            if target not in rel:
                if not (wiki / target).exists():
                    errors.append(f"index.md:{n}: link to missing file {target}")
                continue
            if len(fields) < 3:
                warnings.append(f"index.md:{n}: expected '— type · status · question' after the link")
            page_status = fms.get(target, {}).get("status")
            if indexed[target] and page_status and indexed[target] != page_status:
                errors.append(f"index.md:{n}: status '{indexed[target]}' but {target} says '{page_status}'")
        for name in rel:
            if name not in ("index.md", "log.md") and name not in indexed:
                errors.append(f"{name}: not listed in index.md")

    log = wiki / "log.md"
    if not log.exists():
        errors.append("log.md: missing")
    else:
        last = ""
        for n, line in enumerate(log.read_text(encoding="utf-8").splitlines(), 1):
            if not line.startswith("## "):
                continue
            m = LOG_HEAD.match(line)
            if not m:
                errors.append(f"log.md:{n}: heading not '## [YYYY-MM-DD] <kind> | <title>'")
                continue
            date, kind = m.groups()
            if kind not in LOG_KINDS:
                errors.append(f"log.md:{n}: kind '{kind}' not in {sorted(LOG_KINDS)}")
            if date < last:
                errors.append(f"log.md:{n}: date {date} before previous entry {last} (append-only, oldest first)")
            last = max(last, date)
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", help="wiki folder (default: wikiDir from .claude/handoff.json)")
    args = ap.parse_args(argv)
    wiki = Path(args.dir) if args.dir else wiki_dir_from_config(Path.cwd())
    if not wiki.is_dir():
        print(f"wiki_lint: no wiki folder at {wiki}", file=sys.stderr)
        return 2
    errors, warnings = lint(wiki)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"wiki_lint: {wiki}: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
