#!/usr/bin/env python3
"""copy_page reads the copywriter's stage-9 briefs from runs/copywriter/<brand>/.

    python3 tests/test_copy_page_runs.py

SI-86 (copy page runs). No network, no model, no sips. Built pages and fake
runs live in temp folders; the real runs/ is only read.
"""
import sys
import tempfile
import unittest
from pathlib import Path

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE / "tools"))
sys.path.insert(0, str(LANE))

import copy_page as CP                # noqa: E402

BRIEF = "## THE COPY\n\nline one\n\n## THE OPENINGS\n\nhook one\n\n## WHAT TO WATCH\n\nx\n"


class RunHome(unittest.TestCase):

    def test_no_dead_home(self):
        src = (LANE / "tools" / "copy_page.py").read_text()
        for dead in ("results", "output"):   # joined here so a grep of this folder for the dead path stays empty
            self.assertNotIn("copywriter/" + dead, src)
        for line in src.splitlines():
            self.assertFalse('"copywriter"' in line and '"results"' in line, line)
        self.assertEqual(CP.COPY, CP.P.REPO / "runs" / "copywriter")

    def test_reads_the_run_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            for label in ("zz-brand-01", "other-02"):
                d = Path(tmp) / "zz-brand" / label
                d.mkdir(parents=True)
                (d / "stage9--brief.md").write_text(BRIEF)
            ps = CP.pieces("zz-brand", copy_root=tmp)
        self.assertEqual(len(ps), 1)
        p = ps[0]
        self.assertEqual(p["slug"], "zz-brand-01")
        self.assertEqual(p["run"], "zz-brand-zz-brand-01")
        self.assertEqual(p["copy"], "line one")
        self.assertEqual(p["hooks"], "hook one")

    def test_zero_runs_refuses_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as empty:
            out = Path(tmp) / "out.html"
            with self.assertRaises(SystemExit) as cm:
                CP.build("zz-brand", out, copy_root=empty)
            self.assertIn("zz-brand", str(cm.exception.code))
            self.assertIn("nothing written", str(cm.exception.code))
            self.assertFalse(out.exists())

    def test_the_real_tree_has_pieces(self):
        n = sum(len(CP.pieces(b.name)) for b in CP.COPY.iterdir()
                if b.is_dir() and not b.name.startswith(("_", ".")))
        print(f"\n  real tree: {n} pieces under {CP.COPY}", file=sys.stderr)
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
