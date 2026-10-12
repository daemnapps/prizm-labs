"""Triage v3 names the swipe's style and format (the owner, 2026-10-09 — the
Brand C 3D-animated swipe came back photoreal). The run must carry both."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C


class SwipeStyle(unittest.TestCase):
    def test_reads_both_ids(self):
        t = "LANE: ALREADY AN AD\nSTYLE: family-3d — huge glossy eyes\nFORMAT: `song-ad` — sung story\nONE LINE: x"
        self.assertEqual(C.style_format_from_triage(t), {"style_id": "family-3d", "format_id": "song-ad"})

    def test_new_row_kept_as_new(self):
        self.assertEqual(C.style_format_from_triage("STYLE: new:doll-world — porcelain")["style_id"], "new:doll-world")

    def test_old_triage_has_none(self):
        self.assertEqual(C.style_format_from_triage("LANE: ORGANIC\nONE LINE: y"), {"style_id": None, "format_id": None})

    def test_v3_prompt_asks_for_both(self):
        p = sorted((Path(__file__).resolve().parents[1] / "prompts" / "stage-0-triage").glob("triage-v*-damon.md"),
                   key=lambda f: int(f.stem.split("-v")[1].split("-")[0]))[-1].read_text()
        for line in ("STYLE:", "FORMAT:", "{styles}", "{formats}"):
            self.assertIn(line, p)


if __name__ == "__main__":
    unittest.main()
