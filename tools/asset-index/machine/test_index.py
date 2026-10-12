#!/usr/bin/env python3
"""Tests for the Shared Assets resolver (shared_paths.py) and the local search
(search.py). No network, no drive: every record, walk and map is made in a
temp folder.

    python3 tools/asset-index/machine/test_index.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shared_paths  # noqa: E402
import search  # noqa: E402

MB = 1048576


def make_record(work: Path, collection: str, cid: str, *, filename: str, folder: str, size_mb: float,
                duration: float | None, scenes: list[dict], subject: str = "", setting: str = "",
                usable_for=("b-roll",), talking_head=False, old_path: str | None = None) -> Path:
    d = work / collection / cid
    d.mkdir(parents=True)
    (d / "frame_01.jpg").write_bytes(b"jpg")
    meta = {"size_mb": size_mb}
    if duration:
        meta["duration_s"] = duration
    (d / "clip.json").write_text(json.dumps({
        "clip_id": cid, "filename": filename, "folder": folder,
        "path": old_path or f"/home/x/personal-drive/My Drive/{folder}/{filename}",
        "meta": meta, "frames": [{"file": "frame_01.jpg", "at_s": 1.0}]}))
    (d / "breakdown.json").write_text(json.dumps({
        "scenes": scenes, "subject": subject, "setting": setting, "products_visible": [],
        "shot": ["handheld"], "talking_head": talking_head, "usable_for": list(usable_for)}))
    return d


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="asset-index-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "Shared Assets"
        self.work = self.tmp / "work"
        self.maps = self.work / "_maps"
        self._saved = shared_paths.SHARED_ROOT
        shared_paths.SHARED_ROOT = self.root
        self.addCleanup(setattr, shared_paths, "SHARED_ROOT", self._saved)

    def put(self, rel: str, size_mb: float) -> dict:
        p = self.root / "brands" / "acme" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")
        return {"path": str(p), "name": p.name, "bytes": int(size_mb * MB)}


# ---------------------------------------------------------------- resolver

class Resolver(Base):
    def resolve(self, clip, files):
        by_name, by_norm, by_tail = shared_paths.index_files(files)
        return shared_paths.resolve_one(clip, by_name, by_norm, self.root, by_tail)

    def test_a_unique_name_of_the_right_size_resolves(self):
        f = self.put("content-creators/male/x/25-34/sam/raw/IMG_1.MOV", 40.0)
        r = self.resolve({"filename": "IMG_1.MOV", "folder": "Sam", "meta": {"size_mb": 40.0}}, [f])
        self.assertEqual(r["path"], f["path"])

    def test_a_generic_name_goes_to_the_copy_of_the_right_size_even_when_renamed(self):
        # "4.mov" is also another creator's file; the real copy was renamed with its folder slug
        other = self.put("content-creators/male/x/25-34/wes/raw/4.mov", 3.8)
        real = self.put("content-creators/male/y/18-24/cole/raw/project-1_second-10-videos_4.mov", 34.7)
        r = self.resolve({"filename": "4.mov", "folder": "Cole/Project 1/Second 10 Videos",
                          "meta": {"size_mb": 34.7}}, [other, real])
        self.assertEqual(r["path"], real["path"])

    def test_a_lone_name_of_the_wrong_size_is_refused(self):
        f = self.put("archive/C001.MP4", 2010.0)
        r = self.resolve({"filename": "C001.MP4", "folder": "a", "meta": {"size_mb": 5036.1}}, [f])
        self.assertIsNone(r["path"])
        self.assertIn("size differs", r["why"])

    def test_identical_copies_pick_the_old_folders_words(self):
        a = self.put("archive/zips/IMG_9.MOV", 12.0)
        b = self.put("content-creators/male/x/25-34/malik/raw/IMG_9.MOV", 12.0)
        r = self.resolve({"filename": "IMG_9.MOV", "folder": "Street Interview/Malik",
                          "meta": {"size_mb": 12.0}}, [a, b])
        self.assertEqual(r["path"], b["path"])
        self.assertIn("identical copies", r["how"])

    def test_a_missing_name_is_unresolved(self):
        r = self.resolve({"filename": "nope.mp4", "folder": "", "meta": {"size_mb": 1.0}}, [])
        self.assertIsNone(r["path"])

    def test_build_map_never_returns_a_personal_drive_path(self):
        f = self.put("content-creators/m/x/25-34/sam/raw/IMG_1.MOV", 40.0)
        make_record(self.work, "acme-creators", "c1", filename="IMG_1.MOV", folder="Sam", size_mb=40.0,
                    duration=10.0, scenes=[])
        make_record(self.work, "acme-creators", "c2", filename="gone.MOV", folder="Sam", size_mb=40.0,
                    duration=10.0, scenes=[])
        m = shared_paths.build_map(self.work / "acme-creators", [f], self.root, self.maps)
        self.assertEqual(m["c1"]["path"], f["path"])
        self.assertIsNone(m["c2"]["path"])
        self.assertTrue((self.maps / "acme-creators.json").is_file())
        self.assertEqual(shared_paths.shared_path(self.work / "acme-creators", "c1", self.maps), f["path"])
        self.assertIsNone(shared_paths.shared_path(self.work / "acme-creators", "c2", self.maps))
        for v in m.values():
            self.assertNotIn("personal.com", str(v.get("path")))

    def test_on_shared_rejects_anything_outside_the_root(self):
        self.assertFalse(shared_paths.on_shared("/home/x/personal-drive/My Drive/f.mp4"))
        self.assertTrue(shared_paths.on_shared(str(self.root / "brands" / "acme" / "f.mp4")))


# ---------------------------------------------------------------- search

class Search(Base):
    def setUp(self):
        super().setUp()
        files = [self.put("c/m/x/25-34/a/raw/neck.MOV", 10.0), self.put("c/m/x/25-34/b/raw/box.MOV", 10.0),
                 self.put("c/m/x/25-34/c/raw/talk.MOV", 10.0)]
        make_record(self.work, "acme-creators", "neck", filename="neck.MOV", folder="a", size_mb=10.0,
                    duration=20.0, subject="Adult man, grey t-shirt", setting="Bathroom",
                    scenes=[{"t_start": 0.0, "t_end": 4.0, "visuals": "Man washes hands at the sink.",
                             "spoken": None, "on_screen_text": None},
                            {"t_start": 4.0, "t_end": 9.0,
                             "visuals": "Man runs fingertips along his jawline and neck, razor bumps visible.",
                             "spoken": "these bumps never go away", "on_screen_text": None}])
        make_record(self.work, "acme-creators", "box", filename="box.MOV", folder="b", size_mb=10.0,
                    duration=8.0, subject="Hands", setting="Counter",
                    scenes=[{"t_start": 0.0, "t_end": 8.0, "visuals": "Hands open a black product box, lift the lid.",
                             "spoken": None, "on_screen_text": None}])
        # this one is exactly the shot but does not resolve to Shared Assets — never returned
        make_record(self.work, "acme-creators", "lost", filename="lost.MOV", folder="z", size_mb=10.0,
                    duration=8.0, scenes=[{"t_start": 0.0, "t_end": 8.0,
                                           "visuals": "Man runs fingertips along his jawline and neck, razor bumps.",
                                           "spoken": None, "on_screen_text": None}])
        # a still (no duration) is never footage
        make_record(self.work, "acme-creators", "still", filename="still.jpg", folder="z", size_mb=1.0,
                    duration=None, scenes=[{"t_start": 0, "t_end": 0, "visuals": "jawline neck razor bumps",
                                            "spoken": None, "on_screen_text": None}])
        shared_paths.build_map(self.work / "acme-creators", files, self.root, self.maps)

    def find(self, seen, said="", **kw):
        return search.search(seen, said, "acme", work=self.work, maps=self.maps, **kw)

    def test_the_scene_that_shows_it_wins_with_its_time_range_path_and_frame(self):
        hits = self.find("runs his fingertips along the jawline, razor bumps on the neck",
                         "I can't shave my neck without it bumping up")
        self.assertEqual(hits[0]["clip_id"], "neck")
        self.assertEqual((hits[0]["in"], hits[0]["out"]), (4.0, 9.0))
        self.assertTrue(hits[0]["shared_path"].startswith(str(self.root)))
        self.assertTrue(hits[0]["frame"].endswith("frame_01.jpg"))
        self.assertGreater(hits[0]["score"], 0.3)

    def test_unresolved_clips_and_stills_are_never_returned(self):
        ids = {h["clip_id"] for h in self.find("fingertips jawline neck razor bumps", per=10)}
        self.assertNotIn("lost", ids)
        self.assertNotIn("still", ids)

    def test_a_named_product_the_clip_lacks_is_listed_as_missing(self):
        hits = self.find("opens the box and lifts the lid", core="opens the box, lifts the lid",
                         require=["GADGET"])
        self.assertEqual(hits[0]["clip_id"], "box")
        self.assertEqual(hits[0]["missing"], ["gadget"])
        self.assertIsNotNone(hits[0]["action_match"])

    def test_invented_names_are_dropped_from_the_query(self):
        a = self.find("KEMAR runs fingertips along jawline", drop={"kemar"})
        b = self.find("runs fingertips along jawline")
        self.assertEqual(a[0]["score"], b[0]["score"])

    def test_the_same_question_gets_the_same_answer(self):
        q = "hands open a box"
        self.assertEqual(self.find(q), self.find(q))


if __name__ == "__main__":
    unittest.main()
