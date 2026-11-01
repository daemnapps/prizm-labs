#!/usr/bin/env python3
"""SI-56 (teardown working home): run_kit.index never lists a machine's `_work`
folder as a run — the index, `runs.py health` and the runs filer count filed
runs only.

    /usr/bin/python3 components/run-kit/test_index_work_skip.py

Stdlib only, no key, no network; every tree is a temp folder.
"""
import sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from run_kit import index                                   # noqa: E402


def _tree(t):
    root = Path(t) / "runs"
    w = root / "m" / "_work" / "r1"
    w.mkdir(parents=True)
    (w / "brief-final.md").write_text("# live\n")
    f = root / "m" / "b" / "r2" / "deliverable"
    f.mkdir(parents=True)
    (f / "brief.md").write_text("# filed\n")
    return root


class WorkIsSkipped(unittest.TestCase):
    def test_the_constant(self):
        self.assertEqual(index.WORKING, ("_work",))

    def test_scan_health_and_briefs_see_only_the_filed_run(self):
        with tempfile.TemporaryDirectory() as t:
            root = _tree(t)
            rows = index.scan(root)
            self.assertEqual([r["label"] for r in rows], ["r2"])
            self.assertEqual(rows[0]["path"], "runs/m/b/r2")
            self.assertEqual(index.health(root)["m"]["runs"], 1)
            self.assertEqual([b["label"] for b in index.briefs(machine="m", root=root)], ["r2"])

    def test_other_underscore_slots_are_still_scanned(self):
        with tempfile.TemporaryDirectory() as t:
            root = _tree(t)
            s = root / "m" / "_system" / "r3"
            s.mkdir(parents=True)
            labels = sorted(r["label"] for r in index.scan(root))
            self.assertEqual(labels, ["r2", "r3"])
            self.assertEqual({r["brand"] for r in index.scan(root)}, {"b", "_system"})


if __name__ == "__main__":
    unittest.main()
