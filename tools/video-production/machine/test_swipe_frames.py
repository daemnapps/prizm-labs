"""The real frames of the swipe reach production (2026-10-08).

3.2: an element still to make carries `swipe_frames` (the swipe element cut
out of its real frames), and the make step takes them as "real video frame"
references. 4.4: a first frame carries the swipe frame it recreates as a
COMPOSITION reference, after the faces and the packshot, before the set.
No network: a fake workspace and a fake teardown run in a temp folder."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import elements_check as ec
import element_refs as er
import make_character as mc
import storyboard_plan as sp

JPG = b"\xff\xd8\xff\xe0fake"


def brief(doc):
    return "# a brief\n\n```json\n" + json.dumps(doc) + "\n```\n"


def fake_teardown(root: Path) -> Path:
    """A teardown run with a frame map, frames and two cut-out elements."""
    td = root / "td-run"
    fm = td / "framemap"
    (fm / "frames" / "K01").mkdir(parents=True)
    (fm / "frames" / "K02").mkdir(parents=True)
    (fm / "shots").mkdir()
    rows = []
    for k, a, n in (("K01", 0.0, 8), ("K02", 1.0, 8)):
        for i in range(n):
            t = a + i / 8
            f = f"frames/{k}/{k}-{i:04d}-{t:.3f}.jpg"
            (fm / f).write_bytes(JPG)
            rows.append({"shot": k, "index": i, "t": t, "file": f})
    (fm / "frames" / "index.json").write_text(json.dumps({"fps": 8.0, "frames": rows}))
    from PIL import Image
    for k in ("K01", "K02"):
        Image.new("RGB", (36, 64), (120, 110, 100)).save(fm / "shots" / f"{k}-first.jpg")
    (fm / "framemap.json").write_text(json.dumps({"shots": [
        {"id": "K01", "start": 0, "end": 1, "map": {"who": []}},                       # the empty set
        {"id": "K02", "start": 1, "end": 2, "map": {"who": ["Host (face, torso)"]}}]}))

    def element(kind, name, shots, times):
        folder = fm / "elements" / f"{kind}-{ec.slug(name)}"
        folder.mkdir(parents=True)
        crops = []
        for r in rows:
            if r["shot"] in shots:
                c = f"elements/{folder.name}/{ec.slug(name)}-{Path(r['file']).name}"
                (fm / c).write_bytes(JPG)
                crops.append({"file": c, "frame": r["file"], "shot": r["shot"], "t": r["t"]})
        (folder / "element.json").write_text(json.dumps({
            "name": name, "kind": kind, "shots": shots, "times": times,
            "frames_used": [c["frame"] for c in crops], "crops": crops, "best": crops[3]}))
        return {"kind": kind, "name": name, "folder": f"elements/{folder.name}"}
    (fm / "elements" / "index.json").write_text(json.dumps({"elements": [
        element("person", "Host", ["K01", "K02"], [[0, 1], [1, 2]]),
        element("person", "Assistant", ["K02"], [[1, 2]]),
        element("place", "Studio", ["K01", "K02"], [[0, 1], [1, 2]])]}))
    return td


class SheetAttachesSwipeFrames(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="sf-"))
        (self.root / "components").mkdir(); (self.root / "brands").mkdir()
        self.saved = ec._workspace
        ec._workspace = lambda: self.root
        self.td = fake_teardown(self.root)

    def tearDown(self):
        ec._workspace = self.saved
        shutil.rmtree(self.root, ignore_errors=True)

    def test_to_make_items_carry_their_real_frames(self):
        doc = {"piece": {}, "cast": [{"id": "PRESENTER", "bank_id": "NEW",
                                      "real_reference": "the swipe's host, frame at 0:01.5 (right of frame)"}],
               "world": [{"id": "SET", "bank_id": "NEW", "real_reference": "the swipe's first frame at 0:00",
                          "description": "x"}],
               "scenes": [{"id": "S1", "who": "PRESENTER", "setting_id": "SET", "looks": {"PRESENTER": "look-1"}}]}
        body = ec.sheet(brief(doc), "_b", root=self.root, teardown=self.td)
        host = next(i for i in body["items"] if i["id"] == "PRESENTER")
        sf = host["swipe_frames"]
        self.assertEqual((sf["name"], sf["matched_by"]), ("Host", "named in the brief's real reference"))
        self.assertEqual(sf["at_times"][0]["t"], 1.5)                       # the frame at the time the brief names
        self.assertEqual(sf["at_times"][0]["shot"], "K02")
        self.assertEqual([c["shot"] for c in sf["crops"]], ["K01", "K02"])  # one per shot
        self.assertTrue((self.root / sf["best"]["file"]).is_file())
        self.assertEqual(sf["crops_total"], 16)
        place = next(i for i in body["items"] if i["id"] == "SET")
        self.assertEqual(place["swipe_frames"]["name"], "Studio")
        self.assertEqual(body["teardown"], "td-run")
        # the make step takes them as real video frames when the spec names none
        spec = mc.adopt_swipe_frames({"id": "presenter", "swipe_frames": sf}, None, self.root)
        refs = spec["real_references"]
        self.assertTrue(1 <= len(refs) <= mc.SWIPE_FRAME_REFS)
        self.assertEqual({r["kind"] for r in refs}, {"real video frame"})
        self.assertRegex(refs[0]["from"], r"td-run/source\.mp4 at [\d.]+ s \(frame map K0\d")
        self.assertTrue(all(Path(r["file"]).is_file() for r in refs))
        self.assertEqual(mc.adopt_swipe_frames({"real_references": [1]}, None)["real_references"], [1])

    def test_a_banked_element_and_no_teardown_get_nothing(self):
        doc = {"piece": {}, "cast": [{"id": "HOST", "bank_id": "NEW", "real_reference": "the swipe's host"}],
               "scenes": [{"id": "S1", "who": "HOST", "looks": {"HOST": "look-1"}}]}
        body = ec.sheet(brief(doc), "_b", root=self.root)
        self.assertNotIn("swipe_frames", body["items"][0])


class CompositionReference(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="sf-"))
        (self.root / "components").mkdir(); (self.root / "brands").mkdir()
        self.td = fake_teardown(self.root)
        for pid in ("a", "b", "c"):
            h = self.root / "runs" / "ai-elements" / "_b" / "casting" / pid
            (h / "sheets").mkdir(parents=True)
            (h / "master.jpg").write_bytes(JPG)
            (h / "sheets" / "look-1.jpg").write_bytes(JPG)
        sh = self.root / "runs" / "ai-elements" / "_b" / "sets" / "room" / "plates"
        sh.mkdir(parents=True)
        (sh / "front.jpg").write_bytes(JPG)
        self.run = self.root / "prod"
        self.run.mkdir()
        (self.run / "storyboard.json").write_text(json.dumps({
            "teardown": str(self.td), "sections": [{"scenes": ["S1"], "swipe": {"shots": [{"id": "K02"}]}}]}))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def doc(self, who):
        return {"piece": {}, "cast": [{"id": p.upper(), "bank_id": p} for p in who],
                "world": [{"id": "ROOM", "bank_id": "room"}],
                "scenes": [{"id": "S1", "who": " and ".join(p.upper() for p in who), "setting_id": "ROOM",
                            "to_camera": True, "looks": {p.upper(): "look-1" for p in who}}]}

    def test_every_shot_goes_in_sharp_people_included(self):     # the owner, 2026-10-08: never blur
        doc = self.doc(["a"])
        k, f = er.swipe_frame(doc["scenes"][0], self.run)                   # K02 has the host in it
        self.assertEqual(k, "K02")
        self.assertNotIn("camera", f.name)
        k, f = er.swipe_frame(doc["scenes"][0], self.run, {"copies_swipe_shot": "K01"})   # nobody in K01
        self.assertEqual(k, "K01")
        self.assertEqual(f.resolve(), (self.td / "framemap" / "frames" / "K01" / "K01-0000-0.000.jpg").resolve())
        self.assertIsNone(er.swipe_frame(doc["scenes"][0], None))

    def test_order_masters_then_composition_then_set_then_looks(self):
        doc = self.doc(["a"])
        sw = er.swipe_frame(doc["scenes"][0], self.run)
        got = [w for w, _ in er.refs_for_scene(doc["scenes"][0], doc, "_b", self.root, swipe=sw)]
        self.assertEqual(got, ["A master", "swipe composition K02", "set ROOM · front", "A look look-1"])
        doc = self.doc(["a", "b", "c"])                       # a full house: the outfits drop, the swipe stays
        got = [w for w, _ in er.refs_for_scene(doc["scenes"][0], doc, "_b", self.root, swipe=sw)]
        self.assertEqual(len(got), er.MAX_REFS)
        self.assertEqual(got[3:], ["swipe composition K02", "set ROOM · front"])

    def test_the_swipe_shot_goes_first_and_only_once(self):
        it = {"medias": [{"role": "image_references", "value": "master.jpg"},
                         {"role": "image_references", "value": "K02-camera.jpg"}],
              "swipe_composition": "K02", "params": {"prompt": "p"}}
        out = sp.with_swipe_camera(it, "K02-camera.jpg", "K02")        # the 2 Oct recipe: the swipe shot FIRST (sharp since 10-08)
        self.assertEqual([m["value"] for m in out["medias"]], ["K02-camera.jpg", "master.jpg"])
        self.assertEqual(out["swipe_camera"], "K02")



class SameVideoRuling(unittest.TestCase):
    """The 15 s rule holds by default; a spec naming the owner's ruling for
    THAT video lifts only the 15 s half, never the shared-picture half."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cast = self.tmp / "casting"
        other = cast / "banked"; (other / "reference").mkdir(parents=True)
        (other / "reference" / "a.jpg").write_bytes(JPG + b"a")
        (other / "provenance.json").write_text(json.dumps({"real_references": [
            {"file": "reference/a.jpg", "from": "the swipe — X123, run/source.mp4 at 1.0 s"}]}))
        self.new = cast / "new"; self.new.mkdir()
        (self.new / "b.jpg").write_bytes(JPG + b"b")
        self.spec = {"real_references": [{"file": "b.jpg", "from": "the swipe — X123, run/source.mp4 at 4.5 s"}]}

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_default_refuses(self):
        self.assertTrue(mc.shared_with_cast(self.spec, self.new))

    def test_ruling_lifts_for_that_video(self):
        ok = {**self.spec, "same_video_ruling": {"by": "the owner", "date": "2026-10-08",
                                                 "ruling": "lifted for this swipe", "video": "X123"}}
        self.assertEqual(mc.shared_with_cast(ok, self.new), [])

    def test_ruling_for_another_video_does_not(self):
        other = {**self.spec, "same_video_ruling": {"by": "the owner", "date": "2026-10-08",
                                                    "ruling": "lifted", "video": "Y999"}}
        self.assertTrue(mc.shared_with_cast(other, self.new))

    def test_same_picture_still_refused(self):
        (self.new / "b.jpg").write_bytes(JPG + b"a")
        ok = {**self.spec, "same_video_ruling": {"by": "the owner", "date": "2026-10-08",
                                                 "ruling": "lifted", "video": "X123"}}
        self.assertTrue(mc.shared_with_cast(ok, self.new))

if __name__ == "__main__":
    unittest.main()
