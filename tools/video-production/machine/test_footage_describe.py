"""LD-63 (describe on use) in the footage gate: a scene whose best candidates are name-only video records gets at
most DESCRIBE_N of them described before the cut-or-generate call, never more than DESCRIBE_MAX per brief; a dry run
describes nothing; without `describe` nothing is asked. The describer is a fake; no Drive, no model.

    cd tools/video-production/machine && /usr/bin/python3 -m unittest test_footage_describe
"""
import json
import sys
import types
import unittest
from pathlib import Path

import footage
from footage import shared_paths
from test_footage import Index, broll


class FakeDescribe(types.ModuleType):
    def __init__(self):
        super().__init__("asset_index_describe")
        self.calls = []

    def describe_on_use(self, dirs, usd, reason, brand, dry_run=False):
        self.calls.append({"dirs": [Path(d).name for d in dirs], "dry": dry_run})
        if dry_run:
            return {"described": [], "failed": [], "spent_usd": 0.0, "stopped": None,
                    "would_describe": len(dirs), "est_usd": 0.01 * len(dirs)}
        for d in dirs:
            d = Path(d)
            c = json.loads((d / "clip.json").read_text())
            c.update({"described": True, "meta": {"duration_s": 12.0}, "frames": []})
            (d / "clip.json").write_text(json.dumps(c))
            (d / "breakdown.json").write_text(json.dumps({"scenes": [{
                "t_start": 1.0, "t_end": 6.0, "on_screen_text": None, "spoken": "",
                "visuals": "a woman spreads scrub along her forearm at the kitchen sink"}]}))
        return {"described": [Path(d).name for d in dirs], "failed": [], "spent_usd": 0.01 * len(dirs),
                "stopped": None, "would_describe": len(dirs), "est_usd": 0.01 * len(dirs)}


class Describe(Index):
    def setUp(self):
        Index.setUp(self)
        col = self.work / ("%s-mapped" % self.BRAND)
        mp = {}
        for i in range(6):
            fid = "MAP_%d" % i
            d = col / fid
            d.mkdir(parents=True)
            label = "Shared Assets/brands/%s/content-creators/kitchen-sink-forearm-scrub/raw/clip-%d.mov" % (self.BRAND, i)
            (d / "clip.json").write_text(json.dumps({
                "clip_id": fid, "drive_id": fid, "kind": "video", "described": False, "label": label,
                "words": ["content", "creators", "kitchen", "sink", "forearm", "scrub", "clip"],
                "meta": {"duration_s": 12.0}, "frames": []}))
            mp[fid] = {"label": label}
        (col / "map.json").write_text(json.dumps(mp))
        self.fake = FakeDescribe()
        self.addCleanup(sys.modules.pop, "asset_index_describe", None)
        sys.modules["asset_index_describe"] = self.fake
        footage.lib_search._corpus.cache_clear()
        self.addCleanup(footage.lib_search._corpus.cache_clear)

    def plan(self, n=1):
        return {"brand": self.BRAND, "scenes": [
            broll("S%d" % i, "spreads scrub along her forearm at the kitchen sink", "a woman's forearm at the kitchen sink",
                  "she spreads the scrub along her forearm") for i in range(1, n + 1)]}

    def test_top_n_are_described_then_the_scene_is_decided_on_them(self):
        plan = self.plan()
        res = footage.gate(plan, self.BRAND, work=self.work, maps=self.maps, describe=True)
        self.assertEqual(len(self.fake.calls), 1)
        self.assertLessEqual(len(self.fake.calls[0]["dirs"]), footage.DESCRIBE_N)
        self.assertEqual(res["described"][0]["scene"], "S1")
        self.assertEqual(res["cut"], ["S1"])
        self.assertTrue(plan["scenes"][0]["owned_clip"].startswith("MAP_"))
        self.assertEqual(plan["scenes"][0]["owned_in"], 1.0)

    def test_the_brief_cap_holds_across_scenes(self):
        prev = footage.DESCRIBE_MAX
        footage.DESCRIBE_MAX = 4
        self.addCleanup(setattr, footage, "DESCRIBE_MAX", prev)
        footage.gate(self.plan(3), self.BRAND, work=self.work, maps=self.maps, describe=True)
        self.assertLessEqual(sum(len(c["dirs"]) for c in self.fake.calls), 4)

    def test_a_dry_run_describes_nothing(self):
        plan = self.plan()
        res = footage.gate(plan, self.BRAND, work=self.work, maps=self.maps, describe="dry")
        self.assertTrue(self.fake.calls and all(c["dry"] for c in self.fake.calls))
        self.assertEqual(res["generate"], ["S1"])
        self.assertFalse(any((p / "breakdown.json").exists() for p in (self.work / ("%s-mapped" % self.BRAND)).iterdir()
                             if p.is_dir()))

    def test_without_describe_nothing_is_asked(self):
        res = footage.gate(self.plan(), self.BRAND, work=self.work, maps=self.maps)
        self.assertEqual((self.fake.calls, res["generate"]), ([], ["S1"]))
        self.assertNotIn("described", res)


if __name__ == "__main__":
    unittest.main()
