"""Tests for install-project.sh, the handoff hooks and wiki_lint.py. Run: python3 -m unittest discover -s tests"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
LINT = KIT / "skills/wiki/wiki_lint.py"


def sh(*args: str, cwd: Path | None = None, env: dict | None = None, input: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, env={**os.environ, **(env or {})}, input=input, text=True,
                          capture_output=True, check=False)


class ProjectCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / "proj"
        self.p.mkdir()
        sh("git", "init", "-q", cwd=self.p)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def install(self, *opts: str) -> subprocess.CompletedProcess:
        r = sh(str(KIT / "install-project.sh"), str(self.p), *opts)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def hook(self, name: str, stdin: str = "{}") -> subprocess.CompletedProcess:
        r = sh(str(self.p / ".claude/hooks" / name), cwd=self.p, env={"CLAUDE_PROJECT_DIR": str(self.p)}, input=stdin)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r


class InstallTest(ProjectCase):
    def test_default_install(self) -> None:
        r = self.install()
        for f in [".claude/hooks/handoff_config.sh", ".claude/hooks/session_start_context.sh",
                  "notebooks/knowledge/index.md", "notebooks/knowledge/log.md", "notebooks/knowledge/lessons.md"]:
            self.assertTrue((self.p / f).exists(), f)
        cfg = json.loads((self.p / ".claude/handoff.json").read_text())
        self.assertEqual(cfg["sessionLog"], "notebooks/knowledge/session-log-*.md")
        settings = json.loads((self.p / ".claude/settings.json").read_text())
        self.assertEqual(set(settings["hooks"]), {"SessionStart", "SessionEnd"})
        self.assertIn("agent-kit:project-rules", (self.p / "CLAUDE.md").read_text())
        self.assertIn("{{DATE}}", (KIT / "project-template/wiki/log.md").read_text())
        self.assertNotIn("{{", (self.p / "notebooks/knowledge/log.md").read_text())
        self.assertIn("0 errors", r.stdout)  # seeded wiki passes the lint
        self.assertIn("ok:      SessionStart hook runs", r.stdout)

    def test_idempotent(self) -> None:
        self.install()
        before = {p: p.read_bytes() for p in self.p.rglob("*") if p.is_file() and ".git" not in p.parts}
        r = self.install()
        after = {p: p.read_bytes() for p in self.p.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertEqual(before, after)
        self.assertNotIn("copied:", r.stdout)
        self.assertNotIn("added:", r.stdout)

    def test_keeps_existing_settings_and_files(self) -> None:
        (self.p / ".claude/hooks").mkdir(parents=True)
        (self.p / ".claude/hooks/session_end_snapshot.sh").write_text("mine\n")
        (self.p / ".claude/settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]},
                                                                  "hooks": {"Stop": [{"hooks": []}]}}))
        (self.p / "CLAUDE.md").write_text("# Mine\n\n## Lessons and multi-model work\nown copy\n")
        r = self.install()
        self.assertIn("differs: .claude/hooks/session_end_snapshot.sh", r.stdout)
        self.assertEqual((self.p / ".claude/hooks/session_end_snapshot.sh").read_text(), "mine\n")
        s = json.loads((self.p / ".claude/settings.json").read_text())
        self.assertEqual(s["permissions"], {"allow": ["Bash(ls)"]})
        self.assertIn("Stop", s["hooks"])
        self.assertIn("SessionStart", s["hooks"])
        self.assertNotIn("agent-kit:project-rules", (self.p / "CLAUDE.md").read_text())
        self.install("--update")
        self.assertNotEqual((self.p / ".claude/hooks/session_end_snapshot.sh").read_text(), "mine\n")
        self.assertTrue(list((self.p / ".claude/hooks").glob("session_end_snapshot.sh.bak-*")))

    def test_no_project_skills(self) -> None:
        self.install()
        self.assertFalse((self.p / ".claude/skills").exists())  # /handoff and /wiki are user-level now

    def test_dry_run_writes_nothing(self) -> None:
        self.install("--dry-run")
        self.assertEqual([p.name for p in self.p.iterdir()], [".git"])


class HookTest(ProjectCase):
    def setUp(self) -> None:
        super().setUp()
        self.install("--wiki-dir", "docs/kb", "--session-log", "docs/handoff-*.md")
        self.log = self.p / "docs/handoff-2026-10-08.md"
        self.log.write_text("# log\n\n## Status\n\nSTATUS-LINE-X\n\n## Open\n\n1. OPEN-ITEM-Y\n")

    def test_config_written(self) -> None:
        cfg = json.loads((self.p / ".claude/handoff.json").read_text())
        self.assertEqual((cfg["sessionLog"], cfg["wikiDir"]), ("docs/handoff-*.md", "docs/kb"))
        self.assertIn("docs/kb/lessons.md", cfg["lessons"])
        self.assertTrue((self.p / "docs/kb/index.md").exists())

    def test_start_hook_prints_status_from_configured_log(self) -> None:
        out = self.hook("session_start_context.sh").stdout
        self.assertIn("docs/handoff-2026-10-08.md", out)
        self.assertIn("STATUS-LINE-X", out)
        self.assertIn("OPEN-ITEM-Y", out)
        self.assertIn("docs/kb/lessons.md", out)
        self.assertIn("docs/kb/index.md first", out)

    def test_start_hook_picks_last_log_by_name_not_mtime(self) -> None:
        old = self.p / "docs/handoff-2026-10-01.md"
        old.write_text("## Status\n\nOLD-STATUS\n")  # older log edited after the current one
        t = time.time() - 3600
        os.utime(self.log, (t, t))
        self.assertNotIn("OLD-STATUS", self.hook("session_start_context.sh").stdout)

    def test_end_hook_fresh_log_no_snapshot(self) -> None:
        self.hook("session_end_snapshot.sh", '{"reason": "clear"}')
        self.assertFalse((self.p / ".claude/handoff-auto").exists())

    def test_end_hook_stale_log_snapshot(self) -> None:
        t = time.time() - 2 * 3600
        os.utime(self.log, (t, t))
        self.hook("session_end_snapshot.sh", '{"reason": "clear", "session_id": "abc"}')
        snaps = list((self.p / ".claude/handoff-auto").glob("handoff-auto-*.md"))
        self.assertEqual(len(snaps), 1)
        text = snaps[0].read_text()
        self.assertIn("reason: clear", text)
        self.assertIn("STATUS-LINE-X", text)
        # and the next session is warned
        self.assertIn("WARNING", self.hook("session_start_context.sh").stdout)

    def test_staleMin_from_config(self) -> None:
        cfg = json.loads((self.p / ".claude/handoff.json").read_text())
        cfg["staleMin"] = 300
        (self.p / ".claude/handoff.json").write_text(json.dumps(cfg))
        t = time.time() - 2 * 3600
        os.utime(self.log, (t, t))
        self.hook("session_end_snapshot.sh")
        self.assertFalse((self.p / ".claude/handoff-auto").exists())


class LintTest(ProjectCase):
    def setUp(self) -> None:
        super().setUp()
        self.install()
        self.w = self.p / "notebooks/knowledge"

    def lint(self) -> subprocess.CompletedProcess:
        return sh("python3", str(LINT), cwd=self.p)

    def test_seed_passes(self) -> None:
        self.assertEqual(self.lint().returncode, 0)

    def test_unlisted_page_and_bad_frontmatter(self) -> None:
        (self.w / "plan.md").write_text("---\ntype: plan\nstatus: wip\n---\nbody\n")
        r = self.lint()
        self.assertEqual(r.returncode, 1)
        self.assertIn("plan.md: not listed in index.md", r.stdout)
        self.assertIn("status 'wip'", r.stdout)
        self.assertIn("missing 'updated'", r.stdout)

    def test_index_status_mismatch_and_missing_link(self) -> None:
        idx = self.w / "index.md"
        idx.write_text(idx.read_text().replace("lessons · active", "lessons · done")
                       + "- [Gone](gone.md) — plan · active · ?\n- [Kit](~/tools/x.md) — x · active · ?\n")
        r = self.lint()
        self.assertIn("status 'done' but lessons.md says 'active'", r.stdout)
        self.assertIn("missing file gone.md", r.stdout)
        self.assertNotIn("tools/x.md", r.stdout)

    def test_superseded(self) -> None:
        (self.w / "old.md").write_text("---\ntype: plan\nstatus: superseded\nupdated: 2026-10-01\nsources: []\n"
                                       "superseded_by: lessons.md (see P1)\n---\n")
        idx = self.w / "index.md"
        idx.write_text(idx.read_text() + "- [Old](old.md) — plan · superseded by [x](lessons.md) · ?\n")
        self.assertEqual(self.lint().returncode, 0, self.lint().stdout)
        (self.w / "old.md").write_text("---\ntype: plan\nstatus: superseded\nupdated: 2026-10-01\nsources: []\n---\n")
        self.assertIn("superseded without", self.lint().stdout)

    def test_log_format_and_order(self) -> None:
        log = self.w / "log.md"
        log.write_text(log.read_text() + "\n## [2020-01-01] result | Too early\nx\n## bad heading\n"
                       "## [2030-01-01] gossip | Kind\n")
        out = self.lint().stdout
        self.assertIn("before previous entry", out)
        self.assertIn("heading not", out)
        self.assertIn("kind 'gossip'", out)


if __name__ == "__main__":
    unittest.main()
