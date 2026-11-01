"""The brief index (the owner, 2026-09-30): one row per brief, joined to its
teardown, its production runs and their edits by what those runs record."""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief_index as BI                                     # noqa: E402


def w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text if isinstance(text, str) else json.dumps(text))


class BriefIndex(unittest.TestCase):
    def test_a_brief_joins_to_every_station(self):
        repo = Path(tempfile.mkdtemp())
        r = repo / "runs"
        w(r / "video-writing/zz/a-run/run.json", {"opened": "2026-09-30T00:00:00Z", "production_route": "ai",
                                                  "product": "p", "triage_lane": "ORGANIC",
                                                  "audience": {"_avatar": "av"},
                                                  "market_state": {"awareness": "problem-aware"}})
        w(r / "video-writing/zz/a-run/deliverable/5-brief.md",
          "<!-- swipe-match: PASSED · x -->\nbody\nMANIFEST: COMPLETE · x\n")
        w(r / "video-teardown/zz/a-run/doctrine.json", {"format": "demonstration"})
        w(r / "video-production/zz/p1/run.json",
          {"brief_from": str(r / "video-writing/zz/a-run/deliverable/5-brief.md")})
        w(r / "video-edit/zz/e1/kit/edit-kit.json", {"from_run": str(r / "video-production/zz/p1")})
        w(r / "video-production/zz/other/run.json", {"source_brief": "5-brief.md"})   # old: not joined
        f, n = BI.build(repo)
        row = json.loads((r / "video-writing/index.json").read_text())[0]
        self.assertEqual(n, 1)
        self.assertEqual((row["route"], row["avatar"], row["awareness"], row["format"]),
                         ("ai", "av", "problem-aware", "demonstration"))
        self.assertEqual((row["swipe_match"], row["manifest"]), ("PASSED", "COMPLETE"))
        self.assertEqual(row["teardown"], "runs/video-teardown/zz/a-run")
        self.assertEqual(row["production"], ["runs/video-production/zz/p1"])
        self.assertEqual(row["edit"], ["runs/video-edit/zz/e1"])
        self.assertIn("1 briefs · 0 torn down with no brief yet · 1 produced · 1 edited", f.read_text())
        self.assertEqual(row["status"], "brief")


if __name__ == "__main__":
    unittest.main()
