"""Every clip of a hand-off carries every reference it needs and one full prompt (VIDEO-RULINGS V59)."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load():
    s = importlib.util.spec_from_file_location("t_scene_packet", str(HERE / "scene_packet.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


SP = load()


def shot(i, product=False, place="ROOM", **kw):
    s = {"id": i, "start_picture": "first_frame", "angle": "close", "camera_move": "hold", "face": "eyes on the lens",
         "gestures": ["circles"], "ends_on": "the same hold", "lines": [],
         "subjects": {"people": [{"id": "SAM", "look": "NEW: white tee"}], "place": {"id": place, "is": "a plain room"}}}
    if product:
        s["subjects"]["product"] = {"id": "widget", "name": "WIDGET Pro", "in_shot": []}
    s.update(kw)
    return s


def pack(root, lock, scenes, clips, sheet=True, cast_step=True):
    ws = Path(root) / "ws"
    out = ws / "runs" / "handoffs" / "video-editor" / "acme" / "acme_widget_brief-0001"
    (out / "brief").mkdir(parents=True)
    kit = ws / "runs" / "ai-elements" / "acme" / "products" / "widget"
    (kit / "model").mkdir(parents=True)
    (kit / "kit.json").write_text(json.dumps({"aliases": ["widget"], "what": "the black gadget", "size_cm": {"height": 10, "width": 5}}))
    if sheet:
        (kit / "model" / "product-sheet.png").write_bytes(b"png")
    doc = {"piece": {"product": "widget", "style": "phone"}, "cast": [{"id": "SAM", "name": "SAM", "bank_id": "NEW"}],
           "props": [], "product_lock": lock, "scenes": scenes}
    (out / "brief" / "k-brief.md").write_text("# b\n\n```json\n" + json.dumps(doc) + "\n```\n")
    (out / "elements.json").write_text("[]")
    (out / "clips.json").write_text(json.dumps({"brand": "acme", "style": "", "clips": clips}))
    (out / "CLIPS.md").write_text("# x\n\n## Clips to make\n\n" + "\n".join(
        "### %s · 1.50 s\n\n**Recipe (exact):** %s\n\n- Also use: SAM cast sheet\n- Return: `%s`\n" % (c["id"], c["recipe"], c["return"]) for c in clips))
    steps = [{"n": 1, "asset": "a-01.png", "what": "cast sheet for SAM: build once", "cast_sheet": True, "references": []}] if cast_step else []
    for c in clips:
        steps += [{"n": len(steps) + 1, "asset": "p.png", "what": "start picture for %s" % c["id"], "medium": "image", "job": "3d-print",
                   "references": [], "prompt": "", "draft": True, "print": {"reference": []}},
                  {"n": len(steps) + 2, "asset": Path(c["return"]).name, "what": "clip for %s · silent" % c["id"], "medium": "video",
                   "prompt": "x", "draft": True, "settings": {"endpoint": "m/image-to-video"},
                   "references": [{"n": 1, "kind": "image", "media_role": "start_image", "file": "p.png"}]}]
    (out / "run.json").write_text(json.dumps({"product": "widget", "steps": steps, "handoff": {"folder": "f", "drive": "d"}}))
    return ws, out


def clip(i, scene="S1", recipe="Remake the swipe moment with our person and our product: K10: rolls the bottle on the scalp"):
    return {"id": i, "scene": scene, "tool": "gen.shot", "recipe": recipe, "refs": [], "named_refs": ["SAM cast sheet"],
            "copies": ["K10"], "swipe": [], "return": "returned/%s.mp4" % i}


FF = {"subject": "SAM, right hand at his cheek with its grip left open for the WIDGET", "style": "phone"}


class ScenePacket(unittest.TestCase):
    def run_one(self, lock, scenes, clips, **kw):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        ws, out = pack(t.name, lock, scenes, clips, **kw)
        res = SP.apply(out, ws)
        return res, json.loads((out / "clips.json").read_text())["clips"], json.loads((out / "run.json").read_text())["steps"], out, ws

    def test_the_product_and_the_person_are_attached_not_named(self):
        res, cl, steps, out, _ = self.run_one(["S1: shot S1.1, in SAM's right hand on the cheek, laid on in the edit from real footage, never generated"],
                                              [{"id": "S1", "happens": "works the WIDGET on his cheek", "first_frame": FF, "shots": [shot("S1.1", True)]}], [clip("S1-shot-1")])
        self.assertEqual(res["missing"], {})
        rows = {r["role"]: r for r in cl[0]["packet"]["references"]}
        self.assertTrue((out / rows["product"]["file"]).is_file())
        self.assertEqual(rows["person"]["file"], "returned/a-01.png")
        pic, vid = steps[1], steps[2]
        self.assertEqual([r["packet"] for r in pic["references"]], ["person", "product"])
        self.assertEqual([r.get("packet") for r in vid["references"]], [None, "product"])
        self.assertEqual(vid["settings"]["endpoint"], "m/reference-to-video")
        self.assertNotIn("start_image", [r.get("media_role") for r in vid["references"]])
        self.assertIn("Image 2 is WIDGET Pro", vid["prompt"])

    def test_the_hand_is_never_left_empty_and_the_swipes_action_never_enters(self):
        _, cl, steps, out, _ = self.run_one(["S1: shot S1.1, in SAM's right hand, laid on in the edit from real footage, never generated"],
                                            [{"id": "S1", "happens": "works the WIDGET on his cheek", "first_frame": FF, "shots": [shot("S1.1", True)]}], [clip("S1-shot-1")])
        words = cl[0]["packet"]["start_prompt"] + cl[0]["packet"]["clip_prompt"] + steps[1]["prompt"] + steps[2]["prompt"]
        self.assertIn("holding the WIDGET", words)
        for bad in ("grip left open", "laid on", "never generated", "bottle", "scalp"):
            self.assertNotIn(bad, words)
        self.assertNotIn("SAM cast sheet", (out / "CLIPS.md").read_text())

    def test_a_product_only_in_a_later_shot_is_not_in_the_start_picture(self):
        sc = {"id": "S1", "happens": "Shot 1: looks\nShot 2: uses it", "first_frame": {"subject": "SAM, fingertips on his jaw"},
              "shots": [shot("S1.1"), shot("S1.2", True)]}
        _, cl, steps, _, _ = self.run_one(["S1: shot S1.2, on the cheek"], [sc], [clip("S1-shot-1")])
        self.assertNotIn("WIDGET Pro", steps[1]["prompt"])
        self.assertIn("WIDGET Pro", steps[2]["prompt"])

    def test_one_clip_per_shot_takes_only_its_own_shots_elements(self):
        sc = {"id": "S1", "happens": "Shot 1: looks\nShot 2: uses it", "first_frame": {"subject": "SAM looks"},
              "shots": [shot("S1.1", True), shot("S1.2", True, start_picture="SAM holds the WIDGET up")]}
        _, cl, _, _, _ = self.run_one(["S1: S1.2 in his right hand"], [sc], [clip("S1-shot-1"), clip("S1-shot-2")])
        has = [any(r["role"] == "product" for r in c["packet"]["references"]) for c in cl]
        self.assertEqual(has, [False, True])
        self.assertIn("SAM holds the WIDGET up", cl[1]["packet"]["start_prompt"])

    def test_texture_only_carries_no_pack(self):
        _, cl, _, _, _ = self.run_one(["S1: S1.1, real granular texture on the skin, no package appears"],
                                      [{"id": "S1", "happens": "rubs", "first_frame": {"subject": "a shin"}, "shots": [shot("S1.1", True)]}], [clip("S1-shot-1")])
        row = [r for r in cl[0]["packet"]["references"] if r["role"] == "product"][0]
        self.assertIsNone(row["file"])
        self.assertEqual(cl[0]["packet"]["missing"], [])

    def test_a_missing_sheet_holds_the_clip(self):
        sc = [{"id": "S1", "happens": "works the WIDGET", "first_frame": FF, "shots": [shot("S1.1", True)]}]
        res, _, _, _, _ = self.run_one(["S1: shot S1.1, in his hand"], sc, [clip("S1-shot-1")], sheet=False)
        self.assertIn("no casting sheet", res["missing"]["S1-shot-1"][0])
        res, _, _, _, _ = self.run_one(["S1: shot S1.1, in his hand"], sc, [clip("S1-shot-1")], cast_step=False)
        self.assertIn("SAM", res["missing"]["S1-shot-1"][0])

    def test_words_that_still_leave_it_out_hold_the_clip(self):
        res, _, _, _, _ = self.run_one(["S1: shot S1.1, in his hand"], [{"id": "S1", "happens": "shows the WIDGET beside an empty space",
                                       "first_frame": {"subject": "SAM with the WIDGET"}, "shots": [shot("S1.1", True)]}], [clip("S1-shot-1")])
        self.assertIn("leave the product out", res["missing"]["S1-shot-1"][0])

    def test_running_it_twice_changes_nothing(self):
        _, _, _, out, ws = self.run_one(["S1: shot S1.1, in his hand"], [{"id": "S1", "happens": "works the WIDGET", "first_frame": FF, "shots": [shot("S1.1", True)]}],
                                        [clip("S1-shot-1")])
        a = {f: (out / f).read_text() for f in ("clips.json", "run.json", "CLIPS.md")}
        SP.apply(out, ws)
        for f in a:
            self.assertEqual(a[f].strip(), (out / f).read_text().strip(), f)

    def test_a_place_and_a_prop_we_already_own_by_that_name_ride_as_files(self):
        sh = shot("S1.1", True, place="PORCH")
        sh["subjects"]["props"] = ["Ginger bowl", "glass leg"]
        with tempfile.TemporaryDirectory() as d:
            ws, out = pack(d, ["S1: shot S1.1, in his hand"], [{"id": "S1", "happens": "works the WIDGET", "first_frame": FF, "shots": [sh]}],
                           [clip("S1-shot-1")])
            bank = ws / "runs" / "ai-elements" / "acme"
            for f in ("sets/porch/plates/wide.png", "props/ginger-bowl/picture.jpg", "props/glass-leg-stand/picture.jpg"):
                (bank / f).parent.mkdir(parents=True, exist_ok=True)
                (bank / f).write_bytes(b"png")
            SP.apply(out, ws=ws)
            rows = {r["name"]: r for r in json.loads((out / "clips.json").read_text())["clips"][0]["packet"]["references"]}
        self.assertTrue(rows["PORCH"]["file"] and rows["Ginger bowl"]["file"])
        self.assertIsNone(rows["glass leg"]["file"])          # a near name is never taken

    def test_words_that_save_a_spot_for_the_product_are_read_as_the_product(self):
        for a, b in (("The application area is reserved for the real matte texture.", "shows the product's real matte texture"),
                     ("The area on Yai's left remains clear for the later product composition.", "The product stands on Yai's left")):
            self.assertIn(b, SP.in_scene_words(a))


    def test_more_clips_than_shots_each_says_its_own(self):
        with tempfile.TemporaryDirectory() as d:
            words = "One two three four. Five six seven eight."
            sc = {"id": "S1", "voice": words, "happens": "she talks", "first_frame": {"subject": "SAM"}, "shots": [shot("S1.1")]}
            clips = [{"id": "S1-shot-%d" % i, "scene": "S1", "brief_scene": "S1", "tool": "gen.shot", "recipe": "moment number %d" % i, "secs": 4,
                      "return": "returned/x-%d.mp4" % i, "lips": "on: lips to voice/01.mp3", "route": "shot", "who": ["SAM"], "refs": []} for i in (1, 2)]
            ws, out = pack(d, [], [sc], clips)
            SP.apply(out, ws=ws)
            got = [c["packet"]["clip_prompt"] for c in json.loads((out / "clips.json").read_text())["clips"]]
            self.assertNotEqual(got[0], got[1])
            self.assertTrue("One two three four" in got[0] and "Five six" not in got[0])
            self.assertTrue("Five six seven eight" in got[1] and "One two" not in got[1])


    def test_a_read_over_the_picture_is_never_mouthed(self):
        for kind, cam, says in (("broll", False, False), ("talking", True, True), ("talking", False, True)):
            with tempfile.TemporaryDirectory() as d:
                sh = shot("S1.1", lines=[{"speaker": "sam", "say": "It is gone."}])
                sc = {"id": "S1", "kind": kind, "to_camera": cam, "voice": "It is gone.", "happens": "x", "first_frame": {"subject": "SAM"}, "shots": [sh]}
                clips = [{"id": "S1-shot-1", "scene": "S1", "brief_scene": "S1", "tool": "gen.shot", "recipe": "r", "secs": 4, "return": "returned/x.mp4",
                          "route": "shot", "who": ["SAM"], "refs": []}]
                ws, out = pack(d, [], [sc], clips)
                SP.apply(out, ws=ws)
                got = json.loads((out / "clips.json").read_text())["clips"][0]["packet"]["clip_prompt"]
                self.assertEqual('Says: "It is gone."' in got, says)
                self.assertEqual("nobody speaks on camera" in got, not says)


if __name__ == "__main__":
    unittest.main()
