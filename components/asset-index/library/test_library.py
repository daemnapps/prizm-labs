#!/usr/bin/env python3
"""Tests for the footage library: brand words merge into the shared vocabulary, captions mark and never
reject, the owner's folder is left out, and enrich() dedupes, keeps talking heads out of b-roll and puts
near-best direct b-roll first."""
import json
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(runs: Path):
    os.environ["ASSET_INDEX_RUNS"] = str(runs)
    import importlib.util
    sp = importlib.util.spec_from_file_location("lib_under_test", HERE / "library.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def brand_file(runs: Path, brand="_fixture"):
    d = runs / brand / "library"
    d.mkdir(parents=True)
    (d / "brand-vocabulary.json").write_text(json.dumps({
        "products": {"gadget": ["gadget", "silicone brush"]},
        "looks": {"gadget": "a black silicone brush"},
        "partners": {"values": [{"creator_folder": "pal", "handle": "@pal", "status": "verified partner"}]},
        "brand_handles": ["@fixturebrand"],
        "exclude_words": {"values": ["ownerfolder"]}}))


def record(runs: Path, col: str, rid: str, label: str, scenes: list, talking=False, w=1080, h=1920):
    d = runs / "_fixture" / col / rid
    d.mkdir(parents=True)
    (d / "clip.json").write_text(json.dumps({"clip_id": rid, "label": label, "filename": label.split("/")[-1],
                                             "meta": {"duration_s": 20, "width": w, "height": h}, "frames": []}))
    (d / "breakdown.json").write_text(json.dumps({"scenes": scenes, "subject": "man, 20s", "setting": "bathroom",
                                                  "products_visible": ["silicone brush"], "shot": ["close-up"],
                                                  "talking_head": talking, "quality_notes": []}))


LAB = "Shared Assets/brands/_fixture/content-creators/male/black/25-34/sam/raw/"


class Library(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runs = Path(self.tmp.name)
        brand_file(self.runs)
        record(self.runs, "creators", "c1", LAB + "a.mp4",
               [{"t_start": 0, "t_end": 5, "visuals": "Man uses silicone brush on his face with foam", "on_screen_text": None},
                {"t_start": 5, "t_end": 9, "visuals": "Man uses silicone brush on his cheek", "on_screen_text": "NEW ROUTINE"}])
        record(self.runs, "creators", "c2", "Shared Assets/brands/_fixture/ownerfolder/x.mp4",
               [{"t_start": 0, "t_end": 5, "visuals": "Man uses silicone brush on his face", "on_screen_text": None}])
        self.L = load(self.runs)
        self.rows, self.cov = self.L.build("_fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def test_brand_words_merge(self):
        self.assertIn("gadget", self.L.D["product"]["values"])
        self.assertEqual(self.rows[0]["products"], ["gadget"])

    def test_caption_marks_never_rejects(self):
        marks = {r["scene"]: r["text_marks"] for r in self.rows}
        self.assertEqual(marks[1], ["clean"])
        self.assertIn("caption", marks[2])
        self.assertEqual(len(self.rows), 2)

    def test_owner_folder_left_out(self):
        self.assertFalse(any(r["clip"] == "c2" for r in self.rows))

    def test_filed_people_from_the_folder(self):
        r = self.rows[0]
        self.assertEqual((r["creator_gender"], r["creator_ethnicity"], r["creator_age"]), ("male", "black", "25-34"))

    def test_enrich(self):
        lib = self.L.libdir("_fixture")
        (lib / "library.json").write_text(json.dumps(
            self.rows + [{**self.rows[0], "label": LAB + "talk.mp4", "tier": "P", "clip": "c3"}]))
        self.L._ROWS.clear()
        hits = [{"clip_id": "c1", "shared_path": LAB + "a.mp4", "in": 0, "out": 5, "score": 0.6},
                {"clip_id": "old", "shared_path": LAB + "a.mp4", "in": 0, "out": 5, "score": 0.5},
                {"clip_id": "c3", "shared_path": LAB + "talk.mp4", "in": 0, "out": 5, "score": 0.9}]
        out = self.L.enrich(hits, "_fixture")
        self.assertEqual([h["clip_id"] for h in out], ["c1"])
        self.assertEqual(out[0]["text_marks"], ["clean"])

    def test_a_big_library_splits_into_parts(self):
        lib = self.L.libdir("_fixture")
        lib.mkdir(parents=True, exist_ok=True)
        rows = [{**self.rows[0], "clip": f"c{i}", "shows": "x" * 400} for i in range(60)]
        keep = self.L.PART_BYTES
        try:
            self.L.PART_BYTES = 6000
            files = self.L.write_rows(lib, rows)
            self.assertGreater(len(files), 2)
            self.assertTrue(all((lib / n).stat().st_size <= 6000 for n in files[1:]))
            self.assertEqual([r["clip"] for r in self.L.read_rows(lib / "library.json")], [r["clip"] for r in rows])
            self.L.PART_BYTES = keep
            self.assertEqual(self.L.write_rows(lib, rows[:2]), ["library.json"])
            self.assertEqual(sorted(p.name for p in lib.glob("library*.json")), ["library.json"])
            self.assertEqual(len(self.L.read_rows(lib / "library.json")), 2)
        finally:
            self.L.PART_BYTES = keep

    def test_check_answers_roll_into_a_new_file(self):
        d = self.L.libdir("_fixture") / "check"
        d.mkdir(parents=True, exist_ok=True)
        keep = self.L.PART_BYTES
        try:
            self.L.PART_BYTES = 300
            for i in range(6):
                line = json.dumps({"clip": f"c{i}", "answer": {"polish": "x" * 80}}) + "\n"
                with self.L.check_append_file(d, len(line)).open("a") as f:
                    f.write(line)
            names = [p.name for p in self.L.check_files(d)]
            self.assertEqual(names[0], "results.jsonl")
            self.assertGreater(len(names), 1)
            self.assertEqual([json.loads(x)["clip"] for x in self.L.check_lines(d)], [f"c{i}" for i in range(6)])
        finally:
            self.L.PART_BYTES = keep

    def test_times_snap_to_a_real_shot_change(self):
        self.assertEqual(self.L.snap(2.0, 7.0, [1.5, 6.8, 12.0]), (1.5, 6.8, "shot change"))
        self.assertEqual(self.L.snap(2.0, 7.0, [4.0]), (2.0, 7.0, "label"))
        self.assertEqual(self.L.snap(0.0, 3.0, [2.6]), (0.0, 2.6, "out on a cut"))
        self.assertEqual(self.L.snap(2.0, 7.0, None), (2.0, 7.0, "label"))

    def test_proof_pictures_join_as_proof_rows(self):
        pdir = self.runs / "_fixture" / "proof"
        pdir.mkdir(parents=True)
        (pdir / "proof.json").write_text(json.dumps({"items": [
            {"id": "ba1", "kind": "before-after", "media": "image", "rel": "intake/before-after/Finals/A_Acne.jpg",
             "drive_id": "d1", "problem": "acne", "stage": "final", "layout": "side-by-side", "w": 1080, "h": 1080},
            {"id": "ba2", "kind": "before-after", "media": "image", "rel": "ownerfolder/B.jpg", "drive_id": "d2"}]}))
        (pdir / "tags.json").write_text(json.dumps({"ba1": {"quality": 4, "baked_text": "none", "people": "man 18-29",
                                                            "one_line": "acne before and after"}}))
        rows, _ = self.L.build("_fixture")
        pics = [r for r in rows if r.get("kind") == "picture"]
        self.assertEqual([(r["clip"], r["beat"], r["tier"], r["text_marks"]) for r in pics],
                         [("d1", "proof", "A", ["clean"])])

    def test_a_scene_reaches_its_drive_file(self):
        mount = self.runs / "drives" / "Shared Assets"
        f = mount / "brands" / "_fixture" / "content-creators" / "a.mov"
        f.parent.mkdir(parents=True); f.write_bytes(b"x")
        r = {"clip": "1AbCdEfGhIjKlMnOpQrStUvWxYz012", "label": "Shared Assets/brands/_fixture/content-creators/a.mov"}
        self.assertEqual(self.L.drive_link(r), "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012/view")
        self.assertEqual(self.L.source_file(r, mount), f)
        self.assertIsNone(self.L.source_file(dict(r, label="Shared Assets/brands/_fixture/gone.mov"), mount))
        self.assertIsNone(self.L.drive_link({"clip": "proof_1"}))

    def test_every_clip_gets_its_person(self):
        c = self.L.creator_of
        self.assertEqual(c(LAB + "a.mp4"), "sam")
        self.assertEqual(c("Store/Assets/2. Content/1. Creators/1. Founder/Day/x.MOV @ 0:00",
                           {"path": "/id/Assets/2. Content/1. Creators/1. Founder - Jo Bloggs/Day/x.MOV"}), "jo")
        self.assertEqual(c("Store/Assets/1. Creators/Kim/x.mov"), "kim")
        base = "Shared Assets/brands/_fixture/intake/organic/May/"
        self.assertEqual(c(base + "IG_reel_some_one__2025-05-05.mp4"), "some-one")
        self.assertEqual(c(base + "IG-story-_x.y_-01142023T211934.mp4"), "x-y")
        self.assertEqual(c(base + "mr_j_2022-07-06_01-13-00.mp4"), "mr-j")
        self.assertEqual(c(base + "TT_post_P.A.L_2024-01-01.mp4"), "pal")   # handle the partners table files under 'pal'
        self.assertEqual(c(base + "IMG_2925.mov"), "intake/organic")      # no person in the path or name: bucket kept

    def test_no_library_leaves_hits(self):
        hits = [{"clip_id": "z", "shared_path": "x", "in": 0, "out": 1, "score": 0.3}]
        self.assertEqual(self.L.enrich(hits, "_no_such_brand"), hits)


if __name__ == "__main__":
    unittest.main()
