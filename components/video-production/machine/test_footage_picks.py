#!/usr/bin/env python3
"""Editor picks beside a brief (picks.json, editor-picks/v1): a pick for a B-roll scene makes it a cut from the
picked clip, the ledger lists picks first, a new pick for a scene replaces the old one, and re-applying is stable."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import footage as F  # noqa: E402

LEDGER = {"brief": "x/5-brief.md", "brand": "b", "made": "t", "confident_at": 0.5, "indexed": True,
          "broll": 2, "cut": 0, "generate": 2,
          "scenes": [{"scene": "S1", "kind": "broll", "role": "broll", "shows": "hand", "said": "", "plan": "generate",
                      "candidates": [{"clip_id": "c0", "score": 0.3, "in": 1.0, "out": 2.0, "shared_path": "p0",
                                      "frame": None, "shows": "x", "tier": "B", "text_marks": ["clean"]}]},
                     {"scene": "S2", "kind": "broll", "role": "broll", "shows": "face", "said": "", "plan": "generate",
                      "candidates": []},
                     {"scene": "S3", "kind": "talk", "role": "presenter", "shows": "", "said": "", "plan": "presenter"}]}


def pick(pid, scene, t0=3.0):
    return {"id": pid, "clip_id": pid.split(":")[0], "library_scene": 1, "for_scene": scene, "in": t0, "out": t0 + 2,
            "cut_source": "shot change", "shared_path": "Shared Assets/brands/b/a.mp4", "drive": None, "beat": "mechanism",
            "products": [], "tier": "A", "text_marks": ["caption"], "shows": "device on cheek"}


class Picks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "footage.json").write_text(json.dumps(LEDGER))

    def tearDown(self):
        self.tmp.cleanup()

    def test_pick_makes_scene_a_cut_and_heads_the_ledger(self):
        F.write_picks(self.d, "b", "x", [pick("k1:1", "S1"), pick("k2:4", None)])
        out = json.loads((self.d / "footage.json").read_text())
        s1 = out["scenes"][0]
        self.assertEqual((s1["plan"], s1["candidates"][0]["source"], s1["candidates"][0]["clip_id"]), ("cut", "editor pick", "k1"))
        self.assertEqual((out["cut"], out["generate"]), (1, 1))
        md = (self.d / "footage.md").read_text()
        self.assertIn("## Editor picks", md)
        self.assertIn("any (pool)", md)
        self.assertIn("EDITOR PICK", md)

    def test_new_pick_for_a_scene_replaces_and_reapply_is_stable(self):
        F.write_picks(self.d, "b", "x", [pick("k1:1", "S1")])
        F.write_picks(self.d, "b", "x", [pick("k9:2", "S1", 7.0)])
        doc = json.loads((self.d / "picks.json").read_text())
        self.assertEqual([k["id"] for k in doc["picks"]], ["k9:2"])
        out = json.loads((self.d / "footage.json").read_text())
        out = F.apply_picks(out, doc)
        s1 = out["scenes"][0]
        self.assertEqual([h["clip_id"] for h in s1["candidates"]], ["k9", "c0"])
        self.assertEqual(s1["plan_before_pick"], "generate")

    def test_picks_without_a_ledger_still_save(self):
        (self.d / "footage.json").unlink()
        doc = F.write_picks(self.d, "b", "x", [pick("k1:1", None)])
        self.assertEqual(doc["schema"], "editor-picks/v1")
        self.assertTrue((self.d / "picks.json").is_file())
        self.assertFalse((self.d / "footage.md").exists())


if __name__ == "__main__":
    unittest.main()
