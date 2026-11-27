"""The writers with no test file of their own for this: the who-and-what block reaches the prompt they send (no model).
Read on the first brand on disk that has an avatar with a sub-avatar, so no brand is named here."""
import argparse
import sys
import unittest
from pathlib import Path

C = Path(__file__).resolve().parents[2]
for p in ("creative-strategist/machine", "distinct-six", "video-writing/machine", "video-teardown/machine"):
    sys.path.append(str(C / p))
import who  # noqa: E402


def first():
    for b in sorted(p.name for p in (C.parent / "brands").iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        for a in who.avatars(b):
            for s in who.subs(b, a):
                return b, a, s
    return None


class Rest(unittest.TestCase):
    def setUp(self):
        self.who = first()
        if not self.who:
            self.skipTest("no avatar with a sub-avatar on disk")

    def test_distinct_versions(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("distinct_six_run", str(C / "distinct-six" / "run.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        b = m.who_block(*self.who)
        self.assertIn(who.MARK, b)
        self.assertIn("each version names its own level", b)
        self.assertIn(self.who[2], b)

    def test_director(self):
        import json
        import tempfile
        import director as D
        got = []
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "run.json").write_text(json.dumps({"brand": self.who[0], "declared_audience": {"avatar": self.who[1], "sub": self.who[2]}}))
            D.for_whom(lambda text, tier: got.append(text), t)("THE PROMPT", "designs")
        self.assertIn(who.MARK, got[0])
        self.assertIn(self.who[2], got[0])
        self.assertTrue(got[0].endswith("THE PROMPT"))

    def test_outlier_brief_and_lab_pages_call_the_reader(self):
        for f in ("lab/owner/outlier-brief/tools/brand_context.py", "lab/owner/pages/machine/run.py"):
            p = C.parent / f
            if p.is_file():
                self.assertIn("who", p.read_text())
                self.assertRegex(p.read_text(), r"\.block\(")


if __name__ == "__main__":
    unittest.main()
