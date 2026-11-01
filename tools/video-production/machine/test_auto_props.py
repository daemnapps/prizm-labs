"""P65 (2026-10-21): production on Auto makes a prop the swipe never shows and the bank does not hold — from the
brief's own definition, with real references, reviewed for slop, banked so the elements lock accepts it. Fakes only."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_sp = importlib.util.spec_from_file_location("t_auto_elements", HERE / "auto_elements.py")
AE = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(AE)

DOC = {"piece": {"product": "brilliance-face-scrub"}, "product_lock": ["S5 the Brilliance Face Scrub tube"],
       "world": [{"id": "YAI'S KITCHEN", "bank_id": "yai-s-kitchen"}],
       "props": [{"name": "the half-face model", "size": "three times life size: about 60 cm tall",
                  "look": "a sculpted half-face in pale freckled skin, a dozen brown spots with grey-brown roots"},
                 {"name": "the vague thing", "size": "small"}],
       "scenes": [{"id": "S1", "setting_id": "YAI'S KITCHEN", "source": "K01: she pours", "props": ["the half-face model"]}]}


class MakeAProp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.saved = (AE.WS, AE.CALLS)
        AE.WS = self.ws
        AE.CALLS = self.ws / "runs" / "decisions" / "calls.jsonl"     # never the real decisions log
        sets = self.ws / "runs" / "ai-elements" / "_fixture" / "sets" / "yai-s-kitchen" / "plates"
        sets.mkdir(parents=True)
        (sets / "wide.jpg").write_bytes(b"set")
        self.td = self.ws / "runs" / "video-teardown" / "_work" / "swipe1"
        (self.td / "framemap" / "frames" / "K01").mkdir(parents=True)
        (self.td / "framemap" / "frames" / "K01" / "K01-0000-0.000.jpg").write_bytes(b"frame")
        (self.td / "framemap" / "frames" / "index.json").write_text(json.dumps(
            {"frames": [{"shot": "K01", "t": 0.0, "file": "frames/K01/K01-0000-0.000.jpg"}]}))
        (self.ws / "runs" / "ai-elements" / "_fixture" / "props").mkdir(parents=True)
        self.item = {"kind": "prop", "id": "the half-face model", "bank_id": "the-half-face-model", "scenes": ["S1"]}
        self.sent = []

    def tearDown(self):
        AE.WS, AE.CALLS = self.saved
        self.tmp.cleanup()

    def gen(self, prompt, refs, out):
        self.sent.append((prompt, [Path(r).name for r in refs]))
        Path(out).write_bytes(b"png")
        return {"model": "gpt-image-2.5-sunburst", "file": str(out)}

    def test_the_prop_is_made_from_its_definition_with_real_references_and_banked(self):
        dec, why = AE.prop("_fixture", self.item, self.td, "run1", False, doc=DOC, generate=self.gen,
                           review=lambda *a: [])
        self.assertTrue(dec.startswith("made from the brief's definition"), (dec, why))
        prompt, refs = self.sent[0]
        self.assertIn("three times life size: about 60 cm tall", prompt)
        self.assertIn("grey-brown roots", prompt)
        self.assertIn("no product", prompt)
        self.assertEqual(refs, ["set-wide.jpg", "swipe-K01-0000-0.000.jpg"])
        dst = self.ws / "runs" / "ai-elements" / "_fixture" / "props" / "the-half-face-model"
        prov = json.loads((dst / "provenance.json").read_text())
        self.assertEqual([r["kind"] for r in prov["real_references"]], ["real video frame"])
        self.assertEqual(len(prov["also_attached"]), 1)
        self.assertTrue(all((dst / r["file"]).is_file() for r in prov["real_references"] + prov["also_attached"]))
        self.assertEqual(prov["made_with"]["picture"], "gpt-image-2.5-sunburst")
        self.assertTrue((dst / "prop.md").is_file() and (dst / "picture.png").is_file())
        self.assertTrue(AE._complete(dst, "prop"), "the elements lock accepts it")

    def test_a_matching_prop_starts_from_its_banked_twin(self):
        doc = {**DOC, "props": DOC["props"] + [
            {"name": "the gold pitcher", "size": "22 cm", "look": "clear glass pitcher of gold water"},
            {"name": "the green pitcher", "size": "22 cm", "look": "the matching clear glass pitcher of green water"}]}
        gold = {"kind": "prop", "id": "the gold pitcher", "bank_id": "the-gold-pitcher", "scenes": ["S1"]}
        green = {"kind": "prop", "id": "the green pitcher", "bank_id": "the-green-pitcher", "scenes": ["S1"]}
        AE.prop("_fixture", gold, self.td, "run1", False, doc=doc, generate=self.gen, review=lambda *a: [])
        AE.prop("_fixture", green, self.td, "run1", False, doc=doc, generate=self.gen, review=lambda *a: [])
        self.assertEqual(self.sent[1][1][0], "twin-picture.png", "the green one starts from the gold one")
        self.assertIn("the SAME object", self.sent[1][0])
        self.assertNotIn("twin", "".join(self.sent[0][1]), "the first of the pair has no twin")

    def test_slop_is_remade_once_and_held_if_it_stays(self):
        calls = []
        rv = lambda *a: calls.append(1) or [{"what": "the lid floats", "fix": "seat the lid"}]
        dec, why = AE.prop("_fixture", self.item, self.td, "run1", False, doc=DOC, generate=self.gen, review=rv)
        self.assertEqual(dec, "")
        self.assertIn("the lid floats", why)
        self.assertEqual(len(self.sent), 2, "one picture, one remake with the fixes")
        self.assertIn("seat the lid", self.sent[1][0])
        self.assertEqual(self.sent[1][1], ["picture.png"], "the remake edits the picture alone")
        dst = self.ws / "runs" / "ai-elements" / "_fixture" / "props" / "the-half-face-model"
        self.assertFalse(AE._complete(dst, "prop"), "a held picture is never banked")

    def test_a_product_is_never_drawn_and_nothing_comes_from_words_alone(self):
        tube = {"kind": "prop", "id": "the Brilliance Face Scrub tube", "bank_id": "tube", "scenes": ["S1"]}
        dec, why = AE.prop("_fixture", tube, self.td, "run1", False, doc=DOC, generate=self.gen, review=lambda *a: [])
        self.assertEqual(dec, "")
        self.assertIn("never drawn", why)
        vague = {"kind": "prop", "id": "the vague thing", "bank_id": "vague", "scenes": ["S1"]}
        self.assertIn("no look", AE.prop("_fixture", vague, self.td, "run1", False, doc=DOC, generate=self.gen)[1])
        lone = {"kind": "prop", "id": "the half-face model", "bank_id": "x", "scenes": ["S9"]}
        self.assertIn("no real reference", AE.prop("_fixture", lone, None, "run1", False, doc=DOC, generate=self.gen)[1])
        self.assertEqual(self.sent, [])


class InTheChain(unittest.TestCase):
    """V25 (the owner, 2026-10-21: "ok make sure that's put in the chain"): run_v2 start → auto_elements.run() takes a
    brief whose prop the swipe never shows and the bank does not hold from "left to make" to banked, then the manifest
    re-check and the confirmed sheet — no hand step."""

    def test_an_unshown_unbanked_prop_goes_from_left_to_make_to_banked_and_manifest_complete(self):
        import os
        m = MakeAProp("test_the_prop_is_made_from_its_definition_with_real_references_and_banked")
        m.setUp()
        saved_env = os.environ.get("OUTLIER_SETTINGS")
        try:
            settings = m.ws / "settings.json"
            settings.write_text(json.dumps({"automation": {"production": "auto", "paused": False}}))
            os.environ["OUTLIER_SETTINGS"] = str(settings)
            brief = m.td / "stages" / "5-brief.md"
            brief.parent.mkdir(parents=True)
            # a brief whose only element still to make is the prop: its set is banked, no cast, no product
            sets = m.ws / "runs" / "ai-elements" / "_fixture" / "sets" / "yai-s-kitchen"
            for f in ("set.md", "plates/angle-a.jpg", "plates/angle-b.jpg", "reference/frame.jpg"):
                (sets / f).parent.mkdir(parents=True, exist_ok=True)
                (sets / f).write_bytes(b"x")
            (sets / "provenance.json").write_text(json.dumps({
                "element": "yai-s-kitchen", "kind": "setting", "rights": "ours", "made_with": {"pictures": "x"},
                "drive": "x", "real_references": [{"file": "reference/frame.jpg", "kind": "real video frame", "from": "swipe1"}]}))
            doc = {"world": DOC["world"], "props": DOC["props"], "cast": [],
                   "scenes": [{**DOC["scenes"][0], "kind": "broll", "voice": "none"}]}
            brief.write_text("```json\n" + json.dumps(doc) + "\n```\n")
            run_dir = m.ws / "runs" / "video-production" / "_fixture" / "chain1"
            before = AE.EC.sheet(brief.read_text(), "_fixture", root=m.ws, teardown=m.td)
            self.assertIn("the half-face model", [i["id"] for i in before["to_make"] if i["kind"] == "prop"])
            order = []

            def manifest(td, brand, name):
                order.append("manifest")
                left = AE.EC.sheet(brief.read_text(), brand, root=m.ws, teardown=td)["to_make"]
                return (not left), [i["id"] for i in left]
            res = AE.run(brief, "_fixture", run_dir, generate=lambda *a: order.append("made") or m.gen(*a),
                         review=lambda *a: [], manifest=manifest, confirm=lambda run, by: {"fingerprint": "fp", "by": by})
            self.assertEqual(order, ["made", "manifest"], "the prop is made BEFORE the manifest is re-checked")
            self.assertEqual(res.get("confirmed"), "fp", res)
            self.assertNotIn("left", res)
            calls = (AE.CALLS.read_text() if AE.CALLS.is_file() else "")
            self.assertIn("made from the brief's definition", calls)
        finally:
            if saved_env is None:
                os.environ.pop("OUTLIER_SETTINGS", None)
            else:
                os.environ["OUTLIER_SETTINGS"] = saved_env
            m.tearDown()

    def test_the_chain_calls_it_for_every_run_v2_start(self):
        src = (HERE / "run_v2.py").read_text()
        self.assertIn('_ae = _mod("auto_elements", "vm_auto_elements")', src)
        self.assertIn("_ae.run(Path(a.source), a.brand, _CUR[\"run\"])", src)


if __name__ == "__main__":
    unittest.main()
