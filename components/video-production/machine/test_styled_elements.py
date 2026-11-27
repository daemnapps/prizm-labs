"""A styled ad binds what the style chain banked: sets and products by their kept print in the ad's style, a banked
person's new looks one by one (matched or made), and every start picture starts from its kept 3D print."""
import json
import tempfile
import types
import unittest
from pathlib import Path

import auto_elements as AE
import elements_check as EC
import run as R


def _brief(world_bank="bar", style="family-3d", looks=None):
    doc = {"piece": {"title": "t", "style_id": style, "product": "x"},
           "cast": [{"id": "HERO", "bank_id": "hero"}],
           "world": [{"id": "THE BAR", "bank_id": world_bank, "description": "a bar"}],
           "scenes": [{"id": "S1", "who": "HERO", "setting_id": "THE BAR",
                       "looks": looks or {"HERO": "look-1"}, "voice": "none"}]}
    return "x\n```json\n" + json.dumps(doc) + "\n```\n"


class StyledSetIsBound(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "brands" / "b").mkdir(parents=True)
        (self.ws / "components").mkdir()
        s = self.ws / "runs" / "ai-elements" / "b" / "sets" / "bar"
        s.mkdir(parents=True)
        (s / "picture.png").write_bytes(b"p")
        (s / "element.json").write_text(json.dumps({"id": "bar", "kind": "set", "style_id": "family-3d"}))
        self.set = s
        self.saved = EC._SC[:]
        sc = types.SimpleNamespace(
            is_photoreal=lambda sid: sid in (None, "photoreal"), canonical=lambda sid: sid,
            resolve=lambda brand, kind, eid, sid, ws: (
                {"state": "master", "dir": str(s)} if kind == "set" and eid == "bar" and sid == "family-3d"
                else {"state": "no-master", "dir": None}))
        EC._SC[:] = [sc]

    def tearDown(self):
        EC._SC[:] = self.saved

    def _set_item(self, text):
        body = EC.sheet(text, "b", root=self.ws, drive=False)
        return next(i for i in body["items"] if i["kind"] == "setting")

    def test_a_set_in_the_ads_style_is_banked_by_its_print(self):
        i = self._set_item(_brief())
        self.assertEqual(i["status"], "banked", i["missing"])
        self.assertTrue(i["folder"].endswith("sets/bar"))

    def test_a_photoreal_ad_still_needs_the_plates(self):
        i = self._set_item(_brief(style="photoreal"))
        self.assertEqual(i["status"], "to make")
        self.assertTrue(any("establishing plate" in m for m in i["missing"]))

    def test_a_styled_set_with_no_picture_is_still_to_make(self):
        (self.set / "picture.png").unlink()
        i = self._set_item(_brief())
        self.assertEqual(i["status"], "to make")
        self.assertTrue(any("styled picture" in m for m in i["missing"]))


class NewLooksOneByOne(unittest.TestCase):
    def setUp(self):
        self.p = Path(tempfile.mkdtemp()) / "hero"
        self.p.mkdir()
        (self.p / "looks.json").write_text(json.dumps({"looks": {"look-1": {"outfit": "red silk shirt", "sheet": "sheets/look-1.jpg"}}}))
        (self.p / "spec.json").write_text(json.dumps({"id": "hero", "looks": {"look-1": {"outfit": "red silk shirt"}}}))
        self.built = []

    def _build(self, sp, out=None):
        spec = json.loads(Path(sp).read_text())
        self.built.append(sorted(spec["looks"]))
        (Path(out) / "looks.json").write_text(json.dumps({"looks": {k: {"outfit": v["outfit"]} for k, v in spec["looks"].items()}}))

    def test_a_close_match_binds_and_the_rest_are_made(self):
        got = AE.looks_for(self.p, ["NEW: red silk shirt", "NEW: black tuxedo, black bow tie"], "run", False, build=self._build)
        self.assertEqual(got["NEW: red silk shirt"], "look-1")
        lid = got["NEW: black tuxedo, black bow tie"]
        self.assertTrue(lid.startswith("look-2-black-tuxedo"))
        self.assertEqual(len(self.built), 1)
        # a second run finds the look it added by its words and adds nothing
        again = AE.looks_for(self.p, ["NEW: black tuxedo, black bow tie"], "run", False, build=self._build)
        self.assertEqual(again["NEW: black tuxedo, black bow tie"], lid)

    def test_a_look_whose_print_is_not_kept_yet_stays_unbound(self):
        def stops(sp, out=None):
            raise SystemExit("needs its 3D set print first (GATE-4)")
        with self.assertRaises(SystemExit):
            AE.looks_for(self.p, ["NEW: grey crewneck sweater"], "run", False, build=stops)
        self.assertIn("look-2-grey-crewneck-sweater", json.loads((self.p / "spec.json").read_text())["looks"])

    def test_a_character_wears_its_one_look(self):
        (self.p / "spec.json").write_text(json.dumps({"id": "hero", "shown": "character", "looks": {}}))
        got = AE.looks_for(self.p, ["NEW: white cartoon gloves"], "run", False, build=self._build)
        self.assertEqual(got, {"NEW: white cartoon gloves": "look-1"})
        self.assertEqual(self.built, [])

    def test_bind_points_each_new_look_at_its_own_id(self):
        b = Path(tempfile.mkdtemp()) / "brief.md"
        doc = json.loads(_brief().split("```json\n")[1].split("\n```")[0])
        doc["scenes"] = [{"id": "S1", "looks": {"HERO": "NEW: red silk shirt"}},
                         {"id": "S2", "looks": {"HERO": "NEW: black tuxedo"}}]
        b.write_text("```json\n" + json.dumps(doc) + "\n```\n")
        EC.bind(b, {"HERO.look:red silk shirt": "look-1", "HERO.look:black tuxedo": "look-2-black-tuxedo"})
        out = json.loads(b.read_text().split("```json\n")[1].split("\n```")[0])
        self.assertEqual([s["looks"]["HERO"] for s in out["scenes"]], ["look-1", "look-2-black-tuxedo"])


class StartPictureFromItsPrint(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp()) / "run-1"
        self.run.mkdir()
        (self.run / "brief.md").write_text(_brief())
        self.kept = {"set-bar-family-3d": Path("/prints/bar.png")}
        self.saved = R._set_gate
        R._set_gate = lambda: types.SimpleNamespace(kept_print=lambda brand, name: self.kept.get(name))

    def tearDown(self):
        R._set_gate = self.saved

    def test_the_scenes_set_print_in_the_ads_style(self):
        self.assertEqual(R.start_print({"for": "S1"}, "S1-first", self.run, "nobrand"), Path("/prints/bar.png"))

    def test_the_pictures_own_print_comes_first(self):
        self.kept["run-1-S1-first"] = Path("/prints/own.png")
        self.assertEqual(R.start_print({"for": "S1"}, "S1-first", self.run, "nobrand"), Path("/prints/own.png"))

    def test_no_print_is_none(self):
        self.kept.clear()
        self.assertIsNone(R.start_print({"for": "S1"}, "S1-first", self.run, "nobrand"))


class NewRowBankedInTheStyle(unittest.TestCase):
    def setUp(self):
        self.saved = AE.EC._SC[:]
        AE.EC._SC[:] = [types.SimpleNamespace(
            is_photoreal=lambda sid: sid in (None, "photoreal"), canonical=lambda sid: sid,
            resolve=lambda brand, kind, eid, sid, ws: {"state": "master" if eid == "the-gloves" else "no-master"})]

    def tearDown(self):
        AE.EC._SC[:] = self.saved

    def test_a_new_row_the_style_chain_banked_is_bound(self):
        doc = {"piece": {"style_id": "family-3d"}}
        self.assertEqual(AE.styled_bank("b", "person", "the-gloves", doc), "the-gloves")
        self.assertIsNone(AE.styled_bank("b", "person", "someone-else", doc))
        self.assertIsNone(AE.styled_bank("b", "person", "the-gloves", {"piece": {"style_id": "photoreal"}}))


class PropRemakeNamesItsPrint(unittest.TestCase):
    def test_the_remake_edit_carries_the_kept_print(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "run.json").write_text(json.dumps({}))      # a photoreal ad: the picture model makes the prop
        (tmp / "frame.jpg").write_bytes(b"x"); (tmp / "kept.png").write_bytes(b"k")
        calls = []
        def generate(prompt, refs, out, **kw):
            calls.append(kw); Path(out).write_bytes(b"p"); return {"model": "m"}
        door = types.SimpleNamespace(generate=generate)
        gate = types.SimpleNamespace(kept_print=lambda brand, name: tmp / "kept.png")
        sc = types.SimpleNamespace(canonical=lambda s: s, is_photoreal=lambda s: s in (None, "photoreal"),
                                   _set_queue=lambda: (gate, None))
        saved = {k: getattr(AE, k) for k in ("_mod", "prop_definition", "prop_references", "_is_product", "_twin_prop", "EP")}
        real_mod = AE._mod
        AE._mod = lambda path, name: sc if name == "vm_ae_style_chain" else door if name == "vm_ae_direct_openai" else real_mod(path, name)
        AE.prop_definition = lambda doc, pid: {"name": "pin", "look": "white", "size": "38 cm"}
        AE.prop_references = lambda brand, item, doc, td: [("swipe", tmp / "frame.jpg", "the swipe")]
        AE._is_product = lambda doc, pid: False
        AE._twin_prop = lambda *a: None
        AE.EP = types.SimpleNamespace(elements_home=lambda brand, kind, eid, ws: tmp / "props" / eid)
        reviews = iter([[{"what": "slop", "fix": "less slop"}], []])
        try:
            dec, why = AE.make_prop("b", {"id": "pin", "bank_id": "pin"}, {}, tmp, "run", False,
                                    review=lambda *a: next(reviews))
        finally:
            for k, v in saved.items():
                setattr(AE, k, v)
        self.assertTrue(dec.startswith("made"), why)
        self.assertNotIn("from_print", calls[0])
        self.assertEqual(calls[1].get("from_print"), str(tmp / "kept.png"))


class KeptCopyFollowsTheAcceptedBrief(unittest.TestCase):
    def test_a_brief_edited_after_a_bind_is_kept_again(self):
        b = Path(tempfile.mkdtemp()) / "5-brief.md"
        doc = {"cast": [{"id": "A", "bank_id": "NEW"}, {"id": "B", "bank_id": "NEW"}], "world": [], "scenes": []}
        b.write_text("v1\n```json\n" + json.dumps(doc) + "\n```\n")
        EC.bind(b, {"A": "a"})
        keep = b.with_name("5-brief-before-bind.md")
        self.assertTrue(keep.read_text().startswith("v1"))
        EC.bind(b, {"B": "b"})                       # a second bind of the same line keeps the first copy
        self.assertTrue(keep.read_text().startswith("v1"))
        b.write_text(b.read_text().replace("v1", "v2", 1))   # edited and re-accepted
        EC.bind(b, {"A": "a2"})
        self.assertTrue(keep.read_text().startswith("v2"))


class StyledPropIsItsPrint(unittest.TestCase):
    def test_a_prop_in_the_ads_style_takes_its_kept_print_and_draws_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "run.json").write_text(json.dumps({"style_id": "family-3d"}))
        (tmp / "frame.jpg").write_bytes(b"x"); (tmp / "kept.png").write_bytes(b"kept")
        gate = types.SimpleNamespace(kept_print=lambda brand, name: tmp / "kept.png")
        sc = types.SimpleNamespace(canonical=lambda s: s, is_photoreal=lambda s: s in (None, "photoreal"),
                                   _set_queue=lambda: (gate, None))
        saved = {k: getattr(AE, k) for k in ("_mod", "prop_definition", "prop_references", "_is_product", "_twin_prop", "EP")}
        real_mod = AE._mod
        AE._mod = lambda path, name: sc if name == "vm_ae_style_chain" else real_mod(path, name)
        AE.prop_definition = lambda doc, pid: {"name": "pin", "look": "white", "size": "38 cm"}
        AE.prop_references = lambda brand, item, doc, td: [("swipe", tmp / "frame.jpg", "the swipe")]
        AE._is_product = lambda doc, pid: False
        AE._twin_prop = lambda *a: None
        AE.EP = types.SimpleNamespace(elements_home=lambda brand, kind, eid, ws: tmp / "props" / eid)
        def never(*a, **k):
            raise AssertionError("no picture model call for a styled prop")
        try:
            dec, why = AE.make_prop("b", {"id": "pin", "bank_id": "pin"}, {}, tmp, "run", False,
                                    generate=never, review=never)
        finally:
            for k, v in saved.items():
                setattr(AE, k, v)
        self.assertTrue(dec.startswith("made"), why)
        self.assertEqual((tmp / "props" / "pin" / "picture.png").read_bytes(), b"kept")
        self.assertTrue((tmp / "props" / "pin" / "prop.md").is_file())


class HouseRungIsLedgered(unittest.TestCase):
    def test_a_house_picture_rung_missing_from_providers_is_ledgered_unpriced(self):
        import preflight as PF
        run = Path(tempfile.mkdtemp()) / "r"; run.mkdir()
        saved = PF.house_picture_rung
        PF.house_picture_rung = lambda m: m == "house_rung_x"
        try:
            PF.ledger(run, "house_rung_x", "S1-F1", 0.0, "done")
            with self.assertRaises(SystemExit):
                PF.ledger(run, "nobody_named_this", "S2-F1", 0.0, "done")
        finally:
            PF.house_picture_rung = saved
        rows = json.loads((run / "ledger.json").read_text())
        self.assertEqual(rows[0]["model"], "house_rung_x")
        self.assertIn("unpriced", rows[0]["note"])


class PictureRecordIsKept(unittest.TestCase):
    def test_a_later_pass_keeps_earlier_rows_whose_file_is_there(self):
        run = Path(tempfile.mkdtemp())
        (run / "a.png").write_bytes(b"a")
        (run / "direct.json").write_text(json.dumps({"S1-F1": {"file": str(run / "a.png")},
                                                     "S2-F1": {"file": str(run / "gone.png")}}))
        out = R.direct_merged(run, {"S3-F1": {"file": "new"}})
        self.assertEqual(sorted(out), ["S1-F1", "S3-F1"])


class EditOfAPrintedPictureNamesItsPrint(unittest.TestCase):
    def test_note_print_then_the_door_is_told_the_print(self):
        import direct_openai as DO
        d = Path(tempfile.mkdtemp())
        pic, kp = d / "S1.png", d / "kept.png"
        pic.write_bytes(b"p"); kp.write_bytes(b"k")
        saved = R._set_gate
        R._set_gate = lambda: types.SimpleNamespace(is_any_kept_print=lambda f: str(f) == str(kp))
        try:
            R.note_print(pic, [kp, d / "other.png"])
        finally:
            R._set_gate = saved
        self.assertEqual(json.loads((d / "S1.png.print.json").read_text())["print"], str(kp))
        seen = {}
        saved_gate = DO._people_gate
        DO._people_gate = lambda refs, people, cast, door, fp=None: (_ for _ in ()).throw(SystemExit("stop:" + str(fp)))
        try:
            with self.assertRaises(SystemExit) as e:
                DO.generate("edit", [pic], pic, dry_run=True)
        finally:
            DO._people_gate = saved_gate
        self.assertEqual(str(e.exception), "stop:" + str(kp))


class MadePictureWaitsNoMore(unittest.TestCase):
    def test_status_drops_a_wait_whose_picture_is_on_record(self):
        import ai_lane as AL
        run = Path(tempfile.mkdtemp())
        (run / "S21.png").write_bytes(b"x")
        (run / "direct.json").write_text(json.dumps({"S21": {"file": str(run / "S21.png")}}))
        (run / "set-prints.json").write_text(json.dumps({"waiting": [{"picture": "S21"}, {"picture": "S22"}]}))
        saved = AL.run_dir
        AL.run_dir = lambda r: run
        try:
            st = AL.status({"label": "x"})
        finally:
            AL.run_dir = saved
        self.assertEqual([w["picture"] for w in st["waiting_prints"]], ["S22"])


class WhoIsWhoInWords(unittest.TestCase):
    def test_each_face_is_named_with_its_marks_and_everyone_is_present(self):
        ws = Path(tempfile.mkdtemp())
        run = ws / "runs" / "video-production" / "b" / "r1"; run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"brand": "b"}))
        doc = {"cast": [{"id": "ANA", "bank_id": "ana"}, {"id": "BO", "bank_id": "bo"}],
               "scenes": [{"id": "S1", "who": "ANA, BO", "looks": {"ANA": "look-1"}}]}
        (run / "brief.md").write_text("```json\n" + json.dumps(doc) + "\n```\n")
        for b, who in (("ana", "a beauty mark under the right eye"), ("bo", "a full beard cut square")):
            d = ws / "runs" / "ai-elements" / "b" / "casting" / b; d.mkdir(parents=True)
            (d / "spec.json").write_text(json.dumps({"who": who}))
        saved = R.WS
        R.WS = ws
        try:
            words = R.who_is_who({"for": "S1"}, "S1-F1", ["print.png", "/x/casting/bo/full/master.png",
                                                          "/x/casting/ana/full/sheets/look-1.png"], run)
        finally:
            R.WS = saved
        self.assertIn("image 2 is BO's face", words)
        self.assertIn("image 3 is ANA's outfit", words)
        self.assertIn("beauty mark under the right eye", words)
        self.assertIn("full beard cut square", words)
        self.assertIn("Everyone in this picture: ANA, BO", words)

    def test_a_person_playing_two_rows_is_named_as_the_row_on_screen_in_the_scene_look(self):
        ws = Path(tempfile.mkdtemp())
        run = ws / "runs" / "video-production" / "b" / "r1"; run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"brand": "b"}))
        doc = {"cast": [{"id": "TASHA", "bank_id": "cy"}, {"id": "OFFSCREEN", "bank_id": "cy"}],
               "scenes": [{"id": "S1", "who": "TASHA", "looks": {"TASHA": "look-2"}}]}
        (run / "brief.md").write_text("```json\n" + json.dumps(doc) + "\n```\n")
        d = ws / "runs" / "ai-elements" / "b" / "casting" / "cy"; d.mkdir(parents=True)
        (d / "spec.json").write_text(json.dumps({"who": "curly ponytail, white button-down"}))
        (d / "looks.json").write_text(json.dumps({"looks": {"look-2": {"outfit": "black sports bra, black leggings"}}}))
        saved = R.WS
        R.WS = ws
        try:
            words = R.who_is_who({"for": "S1"}, "S1-F1", ["print.png", "/x/casting/cy/full/master.png"], run)
        finally:
            R.WS = saved
        self.assertIn("image 2 is TASHA's face", words)
        self.assertNotIn("OFFSCREEN", words)
        self.assertIn("in this picture wearing black sports bra, black leggings", words)


class FaceRosterFromTheShotsWords(unittest.TestCase):
    def test_a_person_the_scene_lists_but_the_shot_does_not_place_is_left_out(self):
        run = Path(tempfile.mkdtemp())
        doc = {"cast": [{"id": "ANA", "bank_id": "ana"}, {"id": "BO", "bank_id": "bo"}, {"id": "CY", "bank_id": "cy"}],
               "scenes": [{"id": "S1", "who": "ANA, BO, CY"}]}
        (run / "brief.md").write_text("```json\n" + json.dumps(doc) + "\n```\n")
        it = {"for": "S1", "params": {"prompt": "BO at the left half, ANA at the right half. This picture is the first instant only"}}
        self.assertEqual(R.shot_roster(it, "S1-F1", run), ["BO", "ANA"])
        refs = ["kept.png", "/x/casting/cy/full/master.png", "/x/casting/bo/full/master.png"]
        self.assertEqual(R.shot_refs(it, "S1-F1", refs, run), ["kept.png", "/x/casting/bo/full/master.png"])


class IdentityPicturesFirst(unittest.TestCase):
    def test_print_then_character_then_product_then_the_rest(self):
        d = Path(tempfile.mkdtemp())
        ch = d / "casting" / "gloves"; ch.mkdir(parents=True)
        (ch / "spec.json").write_text(json.dumps({"shown": "character"}))
        refs = [d / "print.png", d / "casting" / "deon" / "master.png", d / "products" / "kit" / "model" / "front.png",
                ch / "master.jpg", d / "swipe.jpg"]
        out = R.refs_in_order(refs, d)
        self.assertEqual(out, [refs[0], refs[3], refs[2], refs[1], refs[4]])


if __name__ == "__main__":
    unittest.main()
