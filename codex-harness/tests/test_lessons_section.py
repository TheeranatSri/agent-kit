"""LESSONS L27: worker lesson drafts with ### sub-headings must survive `harness lessons`."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import lessons_section

hand = "## Status\nok\n\n## Lessons (draft)\n### P1. first\n- Problem: a\n### P2. second\n- Problem: b\n\n## How to verify\nrun\n"
body = lessons_section(hand)
assert '### P1. first' in body and '### P2. second' in body and 'How to verify' not in body, body
assert lessons_section("## Lessons (draft)\n- one line\n") == "- one line"
assert lessons_section("## Status\nnothing\n") == ""
assert lessons_section("# Lessons (draft)\n## A\nx\n# Next\ny") == "## A\nx"
print("ok lessons_section")
