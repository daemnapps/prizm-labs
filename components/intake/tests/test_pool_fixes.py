#!/usr/bin/env python3
"""intake's pool fixes (SI-71) — stdlib unittest, no network, no model.

    python3 components/intake/tests/test_pool_fixes.py

intake#6 a copy row points at the block file swipe-paid really writes ·
intake#4 a pool file that cannot be read holds the run, by name ·
intake#5 the own lane says when its cache is not on this machine ·
intake#7 a hold supersedes an earlier index in the same label folder ·
intake#8 a swipe with no asset is counted.
Runs against test_intake's TINY FAKE WORKSPACE (reached through `AI_WORKSPACE`).
"""
import json
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))                              # appended, never inserted at 0

import test_intake as T                                     # noqa: E402  (puts tools/ on the path)
import gates as G                                           # noqa: E402
import pools                                                # noqa: E402

TRUNCATED = '{"blocks": ['


def check(ws, label):
    return json.loads((ws / "runs/intake/alpha" / label / "check.json").read_text())


class TestCopyFilePointer(T.Case):
    def test_a_copy_row_points_at_the_block_file_swipe_paid_writes(self):
        pool = self.ws / "components/swipe-paid/rivalco"
        T.put(pool / "blocks.json", {"brand": "rivalco", "blocks": [
            {"nn": "01", "slug": "01_big-claim", "headline": "A big claim"},
            {"nn": "02", "slug": "02_other", "primary_text": "other words"}]})
        for slug in ("01_big-claim", "02_other"):
            (pool / "blocks").mkdir(exist_ok=True)
            (pool / "blocks" / f"{slug}.md").write_text("# block\n")
        rows = [r for r in pools.read_paid() if r["kind"] == "copy"]
        self.assertEqual({r["id"] for r in rows},
                         {"swipe:paid:rivalco:block-01_big-claim", "swipe:paid:rivalco:block-02_other"})
        for r in rows:
            self.assertTrue((self.ws / r["asset"]["file"]).is_file(), r["asset"]["file"])


class TestCorruptPoolHolds(T.Case):
    def test_an_unreadable_pool_file_holds_by_name(self):
        for rel in ("components/swipe-paid/rivalco/blocks.json",
                    "components/swipe-paid/judgements.json",
                    "components/swipe-organic/records/avatar-feeds/alpha--some-sub/items.json"):
            with self.subTest(file=rel):
                shutil.rmtree(self.ws)
                T.build(self.ws)
                (self.ws / rel).write_text(TRUNCATED)
                rc, out = self.go("--brand", "alpha", "--label", "u1")
                self.assertEqual(rc, 2)
                self.assertIn(rel, out)
                inputs = check(self.ws, "u1")["inputs"]
                self.assertEqual(inputs["result"], "HELD")
                self.assertTrue(any(rel in p for p in inputs["problems"]), inputs["problems"])
                self.assertFalse((self.ws / "runs/intake/alpha/u1/swipes.jsonl").exists())

    def test_found_counts_only_readable_files_and_forgets_a_repaired_one(self):
        rel = "components/swipe-paid/rivalco/blocks.json"
        good = (self.ws / rel).read_text()
        (self.ws / rel).write_text(TRUNCATED)
        f = pools.found()
        self.assertEqual((f["paid"]["files"], f["paid"]["unreadable"]), (0, [rel]))
        (self.ws / rel).write_text(good)
        f = pools.found()
        self.assertEqual((f["paid"]["files"], f["paid"]["unreadable"]), (1, []))
        rc, _ = self.go("--brand", "alpha", "--label", "u2")
        self.assertEqual(rc, 0)


class TestOwnCache(T.Case):
    def setUp(self):
        super().setUp()
        self.own = self.ws / "components/swipe-paid/own"

    def test_source_own_without_the_cache_holds_naming_the_rebuild(self):
        shutil.rmtree(self.own)
        rc, out = self.go("--brand", "alpha", "--label", "o1", "--source", "own")
        self.assertEqual(rc, 2)
        self.assertIn(G.OWN_REBUILD, out)
        self.assertEqual(check(self.ws, "o1")["inputs"]["result"], "HELD")
        self.assertFalse((self.ws / "runs/intake/alpha/o1/swipes.jsonl").exists())
        rc, out = self.go("--brand", "alpha", "--label", "o2", "--source", "own", "--dry-run")
        self.assertEqual(rc, 2)
        self.assertFalse((self.ws / "runs/intake/alpha/o2").exists())

    def test_a_default_run_without_the_cache_says_so_once(self):
        shutil.rmtree(self.own)
        rc, out = self.go("--brand", "alpha", "--label", "o3")
        self.assertEqual(rc, 0)
        self.assertEqual(out.count(G.OWN_SKIPPED), 1)
        self.assertIn(G.OWN_REBUILD, (self.ws / "runs/intake/alpha/o3/summary.md").read_text())
        rc, out = self.go("--brand", "alpha", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertEqual(out.count(G.OWN_SKIPPED), 1)

    def test_a_run_that_did_not_ask_for_the_own_lane_says_nothing(self):
        rc, out = self.go("--brand", "alpha", "--label", "o4")
        self.assertEqual(rc, 0)
        self.assertNotIn(G.OWN_SKIPPED, out)                 # the fixture's cache is here
        shutil.rmtree(self.own)
        rc, out = self.go("--brand", "alpha", "--label", "o5", "--source", "paid")
        self.assertEqual(rc, 0)
        self.assertNotIn(G.OWN_SKIPPED, out)


class TestSameLabelHold(T.Case):
    def subfolders(self, d):
        return sorted(p.name for p in d.iterdir() if p.is_dir())

    def assert_superseded(self, d, first, before, gate):
        self.assertFalse((d / "swipes.jsonl").exists())
        self.assertFalse((d / "summary.md").exists())
        self.assertEqual((d / "swipes.jsonl.superseded").read_bytes(), first)
        self.assertTrue((d / "summary.md.superseded").is_file())
        run = json.loads((d / "run.json").read_text())
        self.assertIn(gate, run["result"])
        self.assertEqual(run["files"], [])
        self.assertEqual(run["superseded"], ["swipes.jsonl.superseded", "summary.md.superseded"])
        self.assertEqual(self.subfolders(d), before)

    def test_an_elements_hold_supersedes_the_earlier_index(self):
        d = self.ws / "runs/intake/alpha/h1"
        self.assertEqual(self.go("--brand", "alpha", "--label", "h1")[0], 0)
        first, before = (d / "swipes.jsonl").read_bytes(), self.subfolders(d)
        self.assertEqual(self.go("--brand", "alpha", "--label", "h1", "--gates", "hold")[0], 2)
        self.assert_superseded(d, first, before, "elements")

    def test_an_inputs_hold_supersedes_the_earlier_index(self):
        d = self.ws / "runs/intake/alpha/h2"
        self.assertEqual(self.go("--brand", "alpha", "--label", "h2")[0], 0)
        first, before = (d / "swipes.jsonl").read_bytes(), self.subfolders(d)
        (self.ws / "components/swipe-paid/rivalco/blocks.json").write_text(TRUNCATED)
        self.assertEqual(self.go("--brand", "alpha", "--label", "h2")[0], 2)
        self.assert_superseded(d, first, before, "inputs")


class TestAssetNotLocated(T.Case):
    def test_a_swipe_with_no_asset_is_counted(self):
        rc, out = self.go("--brand", "alpha", "--label", "a1")
        self.assertEqual(rc, 0)
        d, recs = self.index("alpha", "a1")
        lost = {}
        for r in recs:
            if not (r["asset"]["url"] or r["asset"]["file"] or r["asset"]["drive"]):
                k = f"{r['source']} · {r['kind']}"
                lost[k] = lost.get(k, 0) + 1
        self.assertEqual(lost, {"own · image": 1, "own · video": 2})
        self.assertEqual(json.loads((d / "run.json").read_text())["counts"]["asset_not_located"], lost)
        summary = (d / "summary.md").read_text()
        self.assertIn("## Asset not located", summary)
        self.assertIn("own · video: **2**", summary)
        self.assertIn("asset not located: 3", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
