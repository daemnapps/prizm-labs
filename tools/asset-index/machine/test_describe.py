#!/usr/bin/env python3
"""LD-63 (describe on use): only undescribed video records are described, into their own record folder; the budget
stops it before a clip starts; a second call on the same id spends nothing; the Drive's daily download limit stops
the batch for the day; a dry run spends nothing and says what it would.

    python3 tools/asset-index/machine/test_describe.py

Fakes only: index_run.one, the Drive check, the key and the token. No network, no model, no Drive.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import describe as D  # noqa: E402
import index_run as IR  # noqa: E402

B = "_brand"
USE = {"model": IR.MODEL, "prompt": 10000, "candidates": 1000, "thoughts": 1000, "total": 12000, "by_modality": []}


class Describe(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ld63-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.runs = self.tmp / "runs"
        self.col = self.runs / B / "content-creators"
        self.col.mkdir(parents=True)
        mp = {}
        for i, kind in enumerate(["video", "video", "video", "image"]):
            fid = "ID_%s_%d" % (kind, i)
            d = self.col / fid
            d.mkdir()
            (d / "clip.json").write_text(json.dumps({
                "clip_id": fid, "drive_id": fid, "kind": kind, "described": False, "words": ["kitchen"],
                "label": "Shared Assets/brands/%s/content-creators/raw/%s.mov" % (B, fid),
                "meta": {"duration_s": 30.0 if kind == "video" else None}}))
            mp[fid] = {"label": "x"}
        (self.col / "map.json").write_text(json.dumps(mp))
        self.calls, self.checked = [], []

        def one(label, out_dir, brand, k, av, fid, tok, record_dir=None):
            self.calls.append(fid)
            d = Path(record_dir)
            (d / "breakdown.json").write_text(json.dumps({"scenes": []}))
            c = json.loads((d / "clip.json").read_text())
            c["described"] = True
            (d / "clip.json").write_text(json.dumps(c))
            return fid, "recorded", dict(USE)
        self.one = one

        def check(fid, tok):
            self.checked.append(fid)
        for p in (mock.patch.object(IR, "drive_check", check), mock.patch.object(IR.gb, "key", lambda: "k"),
                  mock.patch.object(IR, "DriveToken", lambda: object()), mock.patch.object(IR, "avatars", lambda b: []),
                  mock.patch.object(IR, "rate", lambda model=IR.MODEL: ((0.50, 3.00), None))):
            p.start()
            self.addCleanup(p.stop)

    def dirs(self):
        return sorted(p for p in self.col.iterdir() if p.is_dir())

    def ledger(self):
        f = self.runs / B / D.month_collection() / "ledger.json"
        return json.loads(f.read_text())["runs"] if f.is_file() else []

    def test_only_undescribed_videos_and_a_second_call_spends_nothing(self):
        res = D.describe_on_use(self.dirs(), 5.0, "test", brand=B, runs=self.runs, one=self.one)
        self.assertEqual(sorted(res["described"]), ["ID_video_0", "ID_video_1", "ID_video_2"])
        self.assertIn(("ID_image_3", "a picture: describing pictures is a later card"), res["skipped"])
        per = (10000 * 0.5 + 2000 * 3.0) / 1e6
        self.assertAlmostEqual(res["spent_usd"], 3 * per, places=6)
        led = self.ledger()
        self.assertEqual(len(led), 1)
        self.assertAlmostEqual(led[0]["cost_usd"], round(3 * per, 4), places=4)
        self.assertEqual(led[0]["clips"]["reason"], "test")
        again = D.describe_on_use(self.dirs(), 5.0, "test", brand=B, runs=self.runs, one=self.one)
        self.assertEqual((again["described"], again["spent_usd"], len(self.calls)), ([], 0.0, 3))
        self.assertEqual(len(self.ledger()), 1)                        # nothing spent, nothing written

    def test_the_budget_stops_it_before_a_clip_starts(self):
        per = (10000 * 0.5 + 2000 * 3.0) / 1e6
        res = D.describe_on_use(self.dirs(), per * 1.5, "test", brand=B, runs=self.runs, one=self.one)
        self.assertEqual(len(res["described"]), 2)                     # the 2nd started under budget, the 3rd did not
        self.assertTrue(res["stopped"].startswith("budget"))

    def test_the_download_limit_stops_the_batch_for_the_day(self):
        def quota(fid, tok):
            raise IR.QuotaExceeded("Drive download quota (downloadQuotaExceeded) on " + fid)
        with mock.patch.object(IR, "drive_check", quota):
            res = D.describe_on_use(self.dirs(), 5.0, "test", brand=B, runs=self.runs, one=self.one)
        self.assertEqual((res["stopped"], self.calls), ("Drive download quota", []))
        later = D.describe_on_use(self.dirs(), 5.0, "test", brand=B, runs=self.runs, one=self.one)
        self.assertIn("already hit today", later["stopped"])
        self.assertEqual((self.calls, self.checked), ([], []))

    def test_a_refused_read_is_a_failure_and_the_rest_go_on(self):
        def refuse_first(fid, tok):
            if fid == "ID_video_0":
                raise IR.DriveRefused("the Drive refused ID_video_0 (HTTP 403)")
        with mock.patch.object(IR, "drive_check", refuse_first):
            res = D.describe_on_use(self.dirs(), 5.0, "test", brand=B, runs=self.runs, one=self.one)
        self.assertEqual(sorted(res["described"]), ["ID_video_1", "ID_video_2"])
        self.assertEqual(res["failed"][0][0], "ID_video_0")
        self.assertFalse((self.col / "ID_video_0" / "breakdown.json").exists())

    def test_dry_run_spends_nothing_and_says_what_it_would(self):
        res = D.describe_on_use(self.dirs(), 5.0, "test", brand=B, runs=self.runs, one=self.one, dry_run=True)
        self.assertEqual((res["would_describe"], self.calls, self.ledger()), (3, [], []))
        self.assertGreater(res["est_usd"], 0)

    def test_records_under_a_folder(self):
        lab = "Shared Assets/brands/%s/content-creators" % B
        for d in self.dirs():
            pass
        mp = json.loads((self.col / "map.json").read_text())
        for k in mp:
            mp[k]["label"] = lab + "/raw/" + k + ".mov"
        (self.col / "map.json").write_text(json.dumps(mp))
        self.assertEqual(len(D.records_under(B, lab, runs=self.runs)), 4)
        self.assertEqual([p.name for p in D.records_under(B, ids=["ID_video_1"], runs=self.runs)], ["ID_video_1"])


class OneIntoTheRecord(unittest.TestCase):
    """index_run.one(record_dir=): merges into the mapping clip.json; a refused read raises, never 'not footage'."""

    def test_a_refused_probe_raises(self):
        class Tok:
            def header(self):
                return "Authorization: Bearer T\r\n"

        class R:
            returncode, stdout, stderr = 1, "", "Server returned 403 Forbidden (access denied)"
        with mock.patch.object(IR.subprocess, "run", lambda *a, **k: R()):
            with self.assertRaises(IR.DriveRefused):
                IR.ffprobe("https://www.googleapis.com/drive/v3/files/X?alt=media", Tok().header())


if __name__ == "__main__":
    unittest.main()
