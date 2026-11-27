"""The brief editing board (machine/brief_board.py): every swap and trim is a NEW cut-sheet version with its reason in
changes.jsonl and the earlier version untouched; the rough cut is laid from the brief's picks; the edit line's own sheet
keeps each slot on the clock; a regen is priced and held for owner's yes, with nothing made. No network, no live run."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import brief_board as B  # noqa: E402

BRIEF = {"scenes": [
    {"id": "S1", "kind": "broll", "section": "problem", "to_camera": False, "happens": "rubs the bumps along his jaw",
     "voice": "every morning the same bumps"},
    {"id": "S2", "kind": "card", "section": "offer", "to_camera": False, "happens": "the offer card"},
    {"id": "S3", "kind": "broll", "section": "mechanism", "to_camera": False, "happens": "runs the brush over his jaw",
     "voice": "the brush gets under it"},
]}


def raw(clip, scene, beat, tier="A", t_in=0.0, t_out=4.0, label=None):
    return {"clip": clip, "scene": scene, "in": t_in, "out": t_out, "beat": beat, "beats": [beat], "products": [],
            "setting": "bathroom", "person": "man", "shot": "close-up", "vertical": True, "width": 1080, "height": 1920,
            "tier": tier, "text_marks": ["clean"], "source": "creator", "creator": clip, "seconds": t_out - t_in,
            "shows": "man rubs bumps along his jaw with a brush", "creator_gender": "male", "creator_ethnicity": "x",
            "creator_age": "25-34", "label": label or f"Shared Assets/brands/tb/{clip}.mp4", "frame": f"c/{clip}/frame_01.jpg"}


class Board(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = (B.WRITING, B.EDITS, B.REPO, B.library, B.local_file, B.slate)
        B.WRITING, B.EDITS, B.REPO = self.tmp / "runs/video-writing", self.tmp / "runs/video-edit", self.tmp
        d = B.WRITING / "tb" / "brief-x" / "deliverable"
        d.mkdir(parents=True)
        (d / "5-brief.md").write_text("# brief\n\n```json\n" + json.dumps(BRIEF) + "\n```\n")
        (d / "footage.json").write_text(json.dumps({"brief": str(d / "5-brief.md"), "brand": "tb", "indexed": True,
            "confident_at": 0.42, "broll": 2, "cut": 0, "generate": 2, "scenes": [
            {"scene": "S1", "role": "broll", "plan": "generate", "shows": "bumps", "candidates": [{"clip_id": "c1", "frame": None, "shows": "a clip", "tier": "A", "text_marks": ["clean"], "shared_path": "Shared Assets/brands/tb/c1.mp4", "in": 0.0, "out": 4.0, "score": 0.5}]},
            {"scene": "S3", "role": "broll", "plan": "generate", "shows": "brush", "candidates": [{"clip_id": "c3", "frame": None, "shows": "a clip", "tier": "A", "text_marks": ["clean"], "shared_path": "Shared Assets/brands/tb/c3.mp4", "in": 1.0, "out": 3.0, "score": 0.4}]}]}))
        rows = [raw("c1", 1, "problem"), raw("c2", 1, "problem", "B", 2.0, 5.0), raw("c3", 1, "mechanism", "A", 1.0, 3.0),
                raw("c4", 2, "mechanism", "A", 0.0, 6.0)]
        by = {f"{r['clip']}:{r['scene']}": r for r in rows}
        page = {k: {"id": k, "tier": r["tier"], "marks": r["text_marks"], "in": r["in"], "out": r["out"], "shows": r["shows"],
                    "path": r["label"], "file": r["clip"] + ".mp4"} for k, r in by.items()}
        by_label = {}
        for k, r in by.items():
            by_label.setdefault(r["label"], []).append(k)
        self.media = self.tmp / "media.mp4"
        self.media.write_bytes(b"x")
        self.png = self.tmp / "slate.png"
        self.png.write_bytes(b"x")
        B.library = lambda brand: (page, by, by_label)
        B.local_file = lambda brand, r, shared_path=None: (self.media, "proxy") if r else (None, "not on this machine")
        B.slate = lambda run: self.png
        self.run = B.EDITS / "tb" / "brief-x"

    def tearDown(self):
        B.WRITING, B.EDITS, B.REPO, B.library, B.local_file, B.slate = self.saved

    def lines(self):
        return [json.loads(x) for x in (self.run / "changes.jsonl").read_text().splitlines()]

    def sheet(self, n):
        return json.loads((self.run / f"cutsheet-v{n}.json").read_text())

    def test_first_swap_lays_the_rough_cut_then_a_new_version(self):
        B.swap("tb", "brief-x", "S1", "c2:1", "Cleaner picture")
        v1, v2 = self.sheet(1), self.sheet(2)
        self.assertEqual([c["scene"] for c in v1["picture"]], ["S1", "S2", "S3"])      # the brief's order
        self.assertEqual(v1["picture"][0]["owned"]["id"], "c1:1")                       # the ledger's best first
        self.assertTrue(v1["picture"][1]["still"])                                      # the card: a slate until made
        self.assertEqual(v2["picture"][0]["owned"]["id"], "c2:1")
        self.assertAlmostEqual(v2["picture"][1]["start"], 3.0)                          # the clock follows the new clip
        ch = self.lines()
        self.assertEqual([(c["from"], c["to"]) for c in ch], [(None, "cutsheet-v1.json"), ("cutsheet-v1.json", "cutsheet-v2.json")])
        self.assertEqual(ch[1]["why"], "Cleaner picture")
        self.assertIn("c1:1", ch[1]["was"]); self.assertIn("c2:1", ch[1]["now"])

    def test_no_version_is_ever_rewritten(self):
        B.swap("tb", "brief-x", "S1", "c2:1", "a")
        h = hashlib.sha1((self.run / "cutsheet-v2.json").read_bytes()).hexdigest()
        B.trim("tb", "brief-x", "S1", 2.5, 4.5, "Tighter")
        self.assertEqual(hashlib.sha1((self.run / "cutsheet-v2.json").read_bytes()).hexdigest(), h)
        v3 = self.sheet(3)
        self.assertEqual((v3["picture"][0]["source_start"], v3["picture"][0]["duration"]), (2.5, 2.0))
        self.assertEqual(self.lines()[-1]["why"], "Tighter")

    def test_a_swap_and_a_trim_are_the_scenes_pick_in_the_brief(self):
        B.swap("tb", "brief-x", "S1", "c2:1", "a")
        doc = json.loads((B.deliverable("tb", "brief-x") / "picks.json").read_text())
        self.assertEqual(doc["schema"], "editor-picks/v1")
        k = doc["picks"][-1]
        self.assertEqual((k["id"], k["for_scene"], k["clip_id"], k["library_scene"], k["in"], k["out"]), ("c2:1", "S1", "c2", 1, 2.0, 5.0))
        B.trim("tb", "brief-x", "S1", 2.5, 4.5, "Tighter")
        doc = json.loads((B.deliverable("tb", "brief-x") / "picks.json").read_text())
        self.assertEqual([(k["id"], k["in"], k["out"]) for k in doc["picks"]], [("c2:1", 2.5, 4.5)])   # one pick per scene
        led = json.loads((B.deliverable("tb", "brief-x") / "footage.json").read_text())
        s1 = next(r for r in led["scenes"] if r["scene"] == "S1")
        self.assertEqual((s1["plan"], s1["candidates"][0]["source"]), ("cut", "editor pick"))     # the ledger follows

    def test_a_pick_sent_into_the_brief_is_the_first_choice(self):
        (B.deliverable("tb", "brief-x") / "picks.json").write_text(json.dumps({"schema": "editor-picks/v1", "picks": [
            {"id": "c2:1", "clip_id": "c2", "library_scene": 1, "for_scene": None, "in": 2.0, "out": 5.0},
            {"id": "c4:2", "clip_id": "c4", "library_scene": 2, "for_scene": "S3", "in": 1.0, "out": 2.5}]}))
        st = B.state("tb", "brief-x")
        self.assertEqual([(o["id"], o["band"]) for o in st["options"]["S3"]["picked"]], [("c4:2", "pick"), ("c2:1", "pool")])
        B.trim("tb", "brief-x", "S3", 1.0, 2.5, "a")
        s3 = self.sheet(1)["picture"][2]
        self.assertEqual((s3["owned"]["id"], s3["source_start"], s3["duration"]), ("c4:2", 1.0, 1.5))
        self.assertEqual(self.sheet(1)["picture"][0]["owned"]["id"], "c1:1")       # a pool pick is offered, never laid by itself
        B.swap("tb", "brief-x", "S1", "c2:1", "a")                                  # using a pool pick makes it the scene's pick
        doc = json.loads((B.deliverable("tb", "brief-x") / "picks.json").read_text())
        self.assertEqual(sorted((k["id"], k["for_scene"]) for k in doc["picks"]), [("c2:1", "S1"), ("c4:2", "S3")])

    def test_the_edit_lines_sheet_keeps_each_slot_on_the_clock(self):
        self.run.mkdir(parents=True)
        (self.run / "cutsheet-v1.json").write_text(json.dumps({"meta": {"brand": "tb", "label": "brief-x"}, "picture": [
            {"id": "A1", "roll": "a", "src": "a.mp4", "start": 0, "duration": 6, "source_start": 0, "scene": "S0", "why": "talk"},
            {"id": "B1", "roll": "b", "kind": "broll", "src": "old.mp4", "start": 2.0, "duration": 1.5, "source_start": 0, "scene": "S1", "why": "x"}]}))
        B.swap("tb", "brief-x", "S1", "c4:2", "Right product")
        b = self.sheet(2)["picture"][1]
        self.assertEqual((b["start"], b["duration"], b["src"], b["source_start"]), (2.0, 1.5, str(self.media), 0.0))
        B.trim("tb", "brief-x", "S1", 3.0, None, "Truer to the line")
        b = self.sheet(3)["picture"][1]
        self.assertEqual((b["start"], b["duration"], b["source_start"]), (2.0, 1.5, 3.0))
        self.assertEqual(len(self.lines()), 2)                        # no rough cut laid over the edit line's sheet

    def test_regen_is_priced_and_waits_for_owner(self):
        row = B.regen("tb", "brief-x", "S3", "no clip shows the brush")
        self.assertEqual(row["status"], "waiting for owner's yes")
        self.assertEqual(row["spent"], 0)
        self.assertEqual(row["usd"], B.SR.ai_cost(B.seconds_of(BRIEF["scenes"][2])))
        self.assertEqual(B.regen_requests("tb", "brief-x")[-1]["scene"], "S3")
        self.assertFalse(list(self.run.glob("cutsheet-v*.json")))     # asking changes no sheet and makes nothing

    def test_choices_come_in_bands(self):
        st = B.state("tb", "brief-x")
        o = st["options"]["S1"]
        self.assertEqual([x["id"] for x in o["ledger"]], ["c1:1"])
        self.assertTrue(o["ranked"] or o["different"])
        self.assertNotIn("S2", st["options"])                          # a card is made, never cut from footage
        self.assertEqual(st["current"]["S1"]["id"], "c1:1")


if __name__ == "__main__":
    unittest.main()
