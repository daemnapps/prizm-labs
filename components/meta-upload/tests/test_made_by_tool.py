"""Only the image production tool's pictures reach the approval page (image-production RULE GATE-5, 2026-11-11).

A picture with a record in image production's fingerprints (the ledger, or a run record beside it) files; a
hand-edited copy of it, a picture from anywhere else and the tool's words set over one are refused when filing, and a
picture swapped into a card's folder after filing turns the card's check red. The gate sleeps on a checkout whose
image tool carries no switch for it. Everything is written into a temporary root and a temporary ledger; no model,
no network, and the real cards are never touched.

    python3 components/meta-upload/tests/test_made_by_tool.py
"""
import json, os, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import to_check as T  # noqa: E402
import cards as C  # noqa: E402
import made_by_tool as MBT  # noqa: E402

AD = "acme_widget_brief-0001_batch-2026-11-11-%s"
WORDS = {"primary": ["Body"], "headlines": ["H"], "descriptions": ["D"]}
ON = {"on": True, "since": "", "lanes": {"video": True, "image": True, "carousel": True, "creator": False}}


def pic(p, colour=(200, 120, 40), size=(90, 160)):
    from PIL import Image
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(p)
    return p


class Base(unittest.TestCase):
    switch = ON

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.meta = self.tmp / "meta"
        self.env = mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(self.meta), "NO_AD_WORDS": "1",
                                                "IMAGE_MADE_LEDGER": str(self.tmp / "made.jsonl"),
                                                "MADE_BY_TOOL_GATE_OFF": ""})
        self.env.start()
        self.sw = mock.patch.object(MBT.pv(), "switch", lambda: dict(self.switch))
        self.sw.start()
        self.made = pic(self.tmp / "run" / "made.png")
        MBT.pv().stamp(self.made, "engine")                 # stands in for the tool delivering it

    def tearDown(self):
        self.sw.stop()
        self.env.stop()
        shutil.rmtree(self.tmp)

    def file(self, media, lane="image", fmt="flexible", batch="a", **kw):
        return T.to_check("acme", lane, fmt, media, WORDS, [], None, ad_name=AD % batch, product="widget",
                          root=str(self.meta), **kw)

    def other(self, name, colour=(10, 20, 30)):
        return pic(self.tmp / "elsewhere" / name, colour)


class Gate(Base):
    # ---- passes
    def test_a_tool_made_picture_files_and_the_card_carries_its_record(self):
        p = self.file([self.made])
        self.assertEqual(p["state"], "filed")
        c = json.loads((p["target"] / "card.json").read_text())
        self.assertEqual(list(c["made_by_tool"].values())[0]["sha256"], MBT.pv().sha256(self.made))
        self.assertEqual(MBT.check(p["target"], c, "image")[0], True)

    def test_a_tool_made_cover_files_as_a_thumbnail(self):
        vid = self.tmp / "elsewhere" / "v1.mp4"
        vid.parent.mkdir(parents=True, exist_ok=True)
        vid.write_bytes(b"not checked: video files are out of scope")
        with mock.patch.object(T, "_copy", lambda s, d, c: shutil.copy2(s, d)):
            p = self.file([vid], lane="video", thumbs=[self.made])
        self.assertEqual(p["state"], "filed")
        c = json.loads((p["target"] / "card.json").read_text())
        self.assertEqual(list(c["made_by_tool"]), list(c["thumbs"].values()))

    def test_a_copy_moved_anywhere_still_files(self):
        far = self.tmp / "far" / "cover.png"
        far.parent.mkdir(parents=True)
        shutil.copy2(self.made, far)
        self.assertEqual(self.file([far])["state"], "filed")

    def test_a_run_record_beside_the_picture_counts_without_the_ledger(self):
        p = pic(self.tmp / "run2" / "out.png", (1, 2, 3))
        (p.parent / "run.json").write_text(json.dumps({"machine": "image-production",
                                                       "pictures": [{"file": "out.png", "sha256": MBT.pv().sha256(p)}]}))
        self.assertEqual(self.file([p])["state"], "filed")

    # ---- refused
    def refused(self, picture, **kw):
        with self.assertRaises(T.Refused) as e:
            self.file([picture], **kw)
        msg = str(e.exception)
        self.assertIn(picture.name, msg)
        self.assertIn("not made by the image production tool", msg)
        self.assertIn("make.py", msg)
        self.assertFalse(self.meta.exists(), "nothing is written on a refusal")

    def test_a_picture_from_anywhere_else_is_refused(self):
        self.refused(self.other("frame-grab.png"))

    def test_a_hand_edited_copy_is_refused(self):
        from PIL import Image
        bad = self.tmp / "elsewhere" / "edited.png"
        bad.parent.mkdir(parents=True, exist_ok=True)
        im = Image.open(self.made).convert("RGB")
        im.putpixel((0, 0), (255, 0, 0))
        im.save(bad)
        self.refused(bad)

    def test_a_thumbnail_from_anywhere_else_is_refused(self):
        vid = self.tmp / "elsewhere" / "v.mp4"
        grab = self.other("grab.png")
        vid.write_bytes(b"video")
        with self.assertRaises(T.Refused) as e:
            self.file([vid], lane="video", thumbs=[grab])
        self.assertIn("grab.png", str(e.exception))

    def test_the_tools_words_count_only_over_the_tools_picture(self):
        pv = MBT.pv()
        grab = self.other("g.png")
        over_grab, over_made = self.tmp / "elsewhere" / "w1.png", self.tmp / "elsewhere" / "w2.png"
        over_grab.write_bytes(grab.read_bytes() + b"words")           # stands in for the compositor's output
        over_made.write_bytes(self.made.read_bytes() + b"words")
        self.assertIsNone(pv.derive(over_grab, pv.sha256(grab), "words"))
        self.assertIsNotNone(pv.derive(over_made, pv.sha256(self.made), "words"))
        self.refused(over_grab)
        self.assertEqual(self.file([over_made])["state"], "filed")

    def test_a_carousel_slide_turned_to_png_keeps_its_record(self):
        from PIL import Image
        jpg = self.tmp / "elsewhere" / "slide.jpg"
        jpg.parent.mkdir(parents=True, exist_ok=True)
        Image.open(self.made).convert("RGB").save(jpg)
        MBT.pv().stamp(jpg, "engine")                                 # a jpg the tool delivered
        src = [jpg] + [jpg.with_name(f"s{i}.jpg") for i in range(2, 4)]
        for s in src[1:]:
            shutil.copy2(jpg, s)
        p = self.file(src, lane="carousel", fmt="carousel")
        c = json.loads((p["target"] / "card.json").read_text())
        self.assertTrue(all(r.get("converted") for r in c["made_by_tool"].values()))
        self.assertEqual(MBT.check(p["target"], c, "carousel")[0], True)

    # ---- the card check
    def test_a_picture_swapped_into_the_card_after_filing_turns_the_check_red(self):
        p = self.file([self.made])
        c = json.loads((p["target"] / "card.json").read_text())
        f = p["target"] / c["media"][0]
        f.write_bytes(f.read_bytes() + b"x")
        ok, why = MBT.check(p["target"], c, "image")
        self.assertFalse(ok)
        self.assertIn(c["media"][0], why)
        self.assertFalse(C.checks(p["target"], c, online=False)["made_by_tool"]["ok"])

    def test_a_card_filed_before_the_gate_is_left_as_filed(self):
        c = {"made_at": "2026-11-10T09:00:00", "media": ["x.png"]}
        with mock.patch.object(MBT.pv(), "since", lambda: "2026-11-11T18:00:00"):
            self.assertIsNone(MBT.check(self.meta, c, "image"))

    # ---- the switch
    def test_the_switch_turns_one_lane_back(self):
        grab = self.other("g.png")
        with mock.patch.dict(os.environ, {"MADE_BY_TOOL_GATE_OFF": "image"}):
            self.assertEqual(self.file([grab])["state"], "filed")
            with self.assertRaises(T.Refused):
                self.file([grab, grab, grab], lane="carousel", fmt="carousel", batch="b")
        with mock.patch.object(MBT.pv(), "switch", lambda: {"on": True, "lanes": {"image": False}}):
            self.assertFalse(MBT.on("image"))
            self.assertTrue(MBT.on("carousel"))

    def test_the_master_switch_turns_every_lane_back(self):
        with mock.patch.object(MBT.pv(), "switch", lambda: {"on": False}):
            self.assertEqual(self.file([self.other("g.png")])["state"], "filed")

    def test_backfill_records_untouched_pictures_only(self):
        pv = MBT.pv()
        p = pic(self.tmp / "old-run" / "out.png", (9, 9, 9))
        (p.parent / "run.json").write_text(json.dumps({"machine": "image-production", "pictures": [{"file": "out.png"}]}))
        self.assertFalse(pv._in_ledger(pv.sha256(p)))
        self.assertEqual(dict(pv.backfill(p.parent))[p], pv.sha256(p))
        self.assertTrue(pv._in_ledger(pv.sha256(p)))


class NotInstalled(Base):
    """A checkout whose image tool carries no `gate.made_by_tool` switch does not fingerprint its pictures yet:
    the gate sleeps there instead of refusing every picture."""
    switch = {}

    def test_nothing_is_refused_and_no_check_is_added(self):
        p = self.file([self.other("anything.png")])
        self.assertEqual(p["state"], "filed")
        c = json.loads((p["target"] / "card.json").read_text())
        self.assertNotIn("made_by_tool", c)
        self.assertIsNone(MBT.check(p["target"], c, "image"))
        self.assertNotIn("made_by_tool", C.checks(p["target"], c, online=False))


if __name__ == "__main__":
    unittest.main()
